"""Platform-aware checks for protected regular files containing key material."""

from __future__ import annotations

import os
import stat
from pathlib import Path


def is_private_file(path: Path, *, descriptor: int | None = None) -> bool:
    """Return whether *path* is a single-link file private to the current user.

    POSIX systems use owner and mode bits. Windows mode bits do not describe the
    file DACL, so Windows checks the file owner and rejects allow ACEs for any
    principal outside the owner, SYSTEM, Administrators, or Owner Rights.
    When a descriptor is supplied, the check also confirms it still references
    the same file and reads the DACL from that open handle.
    """
    try:
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            return False
        opened = os.fstat(descriptor) if descriptor is not None else None
        if opened is not None and (
            not stat.S_ISREG(opened.st_mode)
            or opened.st_nlink != 1
            or opened.st_ino != info.st_ino
            or opened.st_dev != info.st_dev
        ):
            return False
        if os.name == "nt":
            return _windows_private_acl(path, descriptor)
        current_uid = os.getuid() if hasattr(os, "getuid") else None
        if info.st_mode & 0o077 or (current_uid is not None and info.st_uid != current_uid):
            return False
        if opened is not None and (
            opened.st_mode & 0o077
            or (current_uid is not None and opened.st_uid != current_uid)
        ):
            return False
        return True
    except (OSError, ValueError, TypeError, AttributeError):
        return False


def _windows_private_acl(path: Path, descriptor: int | None) -> bool:
    import ctypes
    import msvcrt
    from ctypes import wintypes

    class _SidAndAttributes(ctypes.Structure):
        _fields_ = [("sid", ctypes.c_void_p), ("attributes", wintypes.DWORD)]

    class _TokenUser(ctypes.Structure):
        _fields_ = [("user", _SidAndAttributes)]

    class _Acl(ctypes.Structure):
        _fields_ = [
            ("revision", ctypes.c_ubyte),
            ("sbz1", ctypes.c_ubyte),
            ("size", wintypes.WORD),
            ("ace_count", wintypes.WORD),
            ("sbz2", wintypes.WORD),
        ]

    class _AceHeader(ctypes.Structure):
        _fields_ = [
            ("ace_type", ctypes.c_ubyte),
            ("ace_flags", ctypes.c_ubyte),
            ("ace_size", wintypes.WORD),
        ]

    advapi32 = ctypes.WinDLL("Advapi32", use_last_error=True)
    kernel32 = ctypes.WinDLL("Kernel32", use_last_error=True)
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    advapi32.OpenProcessToken.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.HANDLE),
    ]
    advapi32.GetTokenInformation.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
    ]
    advapi32.EqualSid.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    advapi32.EqualSid.restype = wintypes.BOOL
    advapi32.ConvertStringSidToSidW.argtypes = [
        wintypes.LPWSTR,
        ctypes.POINTER(ctypes.c_void_p),
    ]
    advapi32.GetSecurityDescriptorDacl.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(wintypes.BOOL),
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.POINTER(wintypes.BOOL),
    ]
    advapi32.GetAce.argtypes = [
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(ctypes.c_void_p),
    ]
    # OWNER_SECURITY_INFORMATION | DACL_SECURITY_INFORMATION
    security_info = 0x00000001 | 0x00000004
    advapi32.GetSecurityInfo.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        wintypes.DWORD,
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.POINTER(ctypes.c_void_p),
    ]
    advapi32.GetNamedSecurityInfoW.argtypes = [
        wintypes.LPWSTR,
        ctypes.c_int,
        wintypes.DWORD,
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.POINTER(ctypes.c_void_p),
    ]

    token = wintypes.HANDLE()
    descriptor_ptr = ctypes.c_void_p()
    converted_sids: list[ctypes.c_void_p] = []
    try:
        if not advapi32.OpenProcessToken(kernel32.GetCurrentProcess(), 0x0008, ctypes.byref(token)):
            return False
        required = wintypes.DWORD()
        advapi32.GetTokenInformation(token, 1, None, 0, ctypes.byref(required))  # TokenUser
        if not required.value:
            return False
        token_buffer = ctypes.create_string_buffer(required.value)
        if not advapi32.GetTokenInformation(
            token, 1, token_buffer, required.value, ctypes.byref(required)
        ):
            return False
        current_sid = ctypes.cast(token_buffer, ctypes.POINTER(_TokenUser)).contents.user.sid

        owner = ctypes.c_void_p()
        dacl = ctypes.c_void_p()
        if descriptor is None:
            result = advapi32.GetNamedSecurityInfoW(
                str(path),
                1,  # SE_FILE_OBJECT
                security_info,
                ctypes.byref(owner),
                None,
                ctypes.byref(dacl),
                None,
                ctypes.byref(descriptor_ptr),
            )
        else:
            handle = wintypes.HANDLE(msvcrt.get_osfhandle(descriptor))
            result = advapi32.GetSecurityInfo(
                handle,
                1,  # SE_FILE_OBJECT
                security_info,
                ctypes.byref(owner),
                None,
                ctypes.byref(dacl),
                None,
                ctypes.byref(descriptor_ptr),
            )
        if result != 0 or not owner.value or not descriptor_ptr.value:
            return False
        if not advapi32.EqualSid(owner, current_sid):
            return False

        present = wintypes.BOOL()
        dacl_ptr = ctypes.c_void_p()
        defaulted = wintypes.BOOL()
        if not advapi32.GetSecurityDescriptorDacl(
            descriptor_ptr,
            ctypes.byref(present),
            ctypes.byref(dacl_ptr),
            ctypes.byref(defaulted),
        ) or not present.value or not dacl_ptr.value:
            return False

        trusted_sids = [current_sid]
        for sid_text in ("S-1-5-18", "S-1-5-32-544", "S-1-3-4"):
            sid = ctypes.c_void_p()
            if not advapi32.ConvertStringSidToSidW(sid_text, ctypes.byref(sid)):
                return False
            converted_sids.append(sid)
            trusted_sids.append(sid)

        acl = ctypes.cast(dacl_ptr, ctypes.POINTER(_Acl)).contents
        deny_types = {1, 6, 10, 12}
        for index in range(acl.ace_count):
            ace = ctypes.c_void_p()
            if not advapi32.GetAce(dacl_ptr, index, ctypes.byref(ace)) or not ace.value:
                return False
            header = ctypes.cast(ace, ctypes.POINTER(_AceHeader)).contents
            if header.ace_type in deny_types:
                continue
            if header.ace_type != 0:  # ACCESS_ALLOWED_ACE_TYPE; reject unknown grant types.
                return False
            ace_address = ctypes.cast(ace, ctypes.c_void_p).value
            ace_sid = ctypes.c_void_p(ace_address + 8)  # header + access mask
            if not any(advapi32.EqualSid(ace_sid, trusted) for trusted in trusted_sids):
                return False
        return True
    except (OSError, ValueError, TypeError, AttributeError, ctypes.ArgumentError):
        return False
    finally:
        for sid in converted_sids:
            kernel32.LocalFree(sid)
        if descriptor_ptr.value:
            kernel32.LocalFree(descriptor_ptr)
        if token:
            kernel32.CloseHandle(token)
