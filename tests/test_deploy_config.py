"""Layer 1 for the production deployment kit (D047): files read, nothing started.

docker-compose.prod.yml puts Caddy in front and takes the gateway's port away;
the Caddyfile sends everything to the gateway; the server scripts stop at the
first failing command, and the deploy never ships a .env.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[1]
PROD = ROOT / "docker-compose.prod.yml"
CADDYFILE = ROOT / "deploy" / "Caddyfile"
SCRIPTS = sorted((ROOT / "deploy" / "vps").glob("*.sh"))


class _ComposeLoader(yaml.SafeLoader):
    """SafeLoader that also reads compose's merge tags (`!reset`, `!override`)."""


def _tagged(loader: yaml.SafeLoader, tag: str, node: yaml.Node):
    if isinstance(node, yaml.SequenceNode):
        value = loader.construct_sequence(node, deep=True)
    elif isinstance(node, yaml.MappingNode):
        value = loader.construct_mapping(node, deep=True)
    else:
        value = loader.construct_scalar(node)
    return {"tag": "!" + tag, "value": value}


_ComposeLoader.add_multi_constructor("!", _tagged)


@pytest.fixture(scope="module")
def prod() -> dict:
    return yaml.load(PROD.read_text(encoding="utf-8"), Loader=_ComposeLoader)


def _env(service: dict) -> dict:
    env = service.get("environment", {})
    assert isinstance(env, dict), "environment as a mapping, so the merge with the base is by key"
    return env


# ================================================================= compose override


def test_speech_builds_with_silero_without_overriding_the_whisper_model():
    base = yaml.load(
        (ROOT / "docker-compose.yml").read_text(encoding="utf-8"), Loader=_ComposeLoader
    )
    speech = base["services"]["speech"]
    assert str(speech["build"]["args"]["VAD"]) == "1"
    assert "AICEFR_WHISPER_MODEL" not in speech["environment"]


def test_caddy_is_the_only_public_entry_on_80_and_443(prod):
    caddy = prod["services"]["caddy"]
    assert caddy["image"].startswith("caddy:2")
    assert {"80:80", "443:443", "443:443/udp"} <= set(caddy["ports"])
    assert "./deploy/Caddyfile:/etc/caddy/Caddyfile:ro" in caddy["volumes"]
    assert caddy["restart"] == "unless-stopped"
    assert "gateway" in caddy["depends_on"]


def test_the_gateway_publishes_nothing_in_production(prod):
    ports = prod["services"]["gateway"]["ports"]
    # `!reset []` drops the base file's 8000:80 instead of appending to it.
    assert ports == {"tag": "!reset", "value": []}


@pytest.mark.parametrize("name", ["core", "web"])
def test_core_and_web_mark_cookies_secure_and_know_their_https_address(prod, name):
    env = _env(prod["services"][name])
    assert str(env["AICEFR_HTTPS_ONLY"]) == "1"
    assert env["AICEFR_PUBLIC_URL"].startswith("https://${AICEFR_DOMAIN:?")


def test_the_domain_is_required_not_defaulted(prod):
    domain = _env(prod["services"]["caddy"])["AICEFR_DOMAIN"]
    assert re.fullmatch(r"\$\{AICEFR_DOMAIN:\?[^}]+\}", domain)


def test_every_service_rotates_its_log(prod):
    base = yaml.load(
        (ROOT / "docker-compose.yml").read_text(encoding="utf-8"), Loader=_ComposeLoader
    )
    services = set(base["services"]) | {"caddy"}
    assert services <= set(prod["services"])
    for name in services:
        logging = prod["services"][name]["logging"]
        assert logging["driver"] == "json-file", name
        assert logging["options"] == {"max-size": "10m", "max-file": "3"}, name


def test_the_gateway_takes_the_client_address_from_caddy(prod):
    # Otherwise every visitor shares Caddy's address and one login rate limit.
    content = prod["configs"]["gateway_realip"]["content"]
    assert "real_ip_header X-Forwarded-For;" in content
    assert "set_real_ip_from 0.0.0.0/0" not in content
    mounts = prod["services"]["gateway"]["configs"]
    assert any(m["target"].startswith("/etc/nginx/conf.d/") for m in mounts)


# ================================================================= Caddyfile


def test_the_caddyfile_serves_the_domain_and_proxies_to_the_gateway():
    text = CADDYFILE.read_text(encoding="utf-8")
    assert re.search(r"^\{\$AICEFR_DOMAIN\}\s*\{", text, re.MULTILINE)
    assert re.search(r"^\s*reverse_proxy\s+gateway:80\s*$", text, re.MULTILINE)


def test_the_caddyfile_limits_bodies_like_the_gateway_and_never_overrides_app_headers():
    text = CADDYFILE.read_text(encoding="utf-8")
    nginx = (ROOT / "deploy" / "gateway" / "default.conf.template").read_text(encoding="utf-8")
    nginx_mib = int(re.search(r"client_max_body_size\s+(\d+)m;", nginx).group(1))
    assert re.search(rf"max_size\s+{nginx_mib}MiB", text)
    # The services set these themselves; Caddy only fills in where they are missing.
    for header in ("Strict-Transport-Security", "Content-Security-Policy", "Referrer-Policy"):
        assert re.search(rf"^\s*\?{header}\s", text, re.MULTILINE), header


# ================================================================= server scripts


def test_the_server_scripts_exist_and_stop_at_the_first_error():
    names = {p.name for p in SCRIPTS}
    assert {"bootstrap.sh", "deploy.sh", "backup.sh", "restore.sh"} <= names
    for script in SCRIPTS:
        lines = [
            line.strip()
            for line in script.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        assert lines[0] == "set -euo pipefail", script.name


def test_the_deploy_never_ships_an_env_file():
    text = (ROOT / "deploy" / "vps" / "deploy.sh").read_text(encoding="utf-8")
    assert "--exclude='.env'" in text
    assert "--exclude='.env.*'" in text
    assert "--delete-excluded" not in text  # would remove the server's own .env
    assert "-f docker-compose.yml -f docker-compose.prod.yml up -d --build --remove-orphans" in text


METERED = (
    "AICEFR_METERING",
    "AICEFR_PRICE_FIRST_MINUTE_RUNS",
    "AICEFR_PRICE_EXTRA_MINUTE_RUNS",
    "AICEFR_PRICE_PRACTICE_FACTOR",
    "AICEFR_IDPOINT_PER_RUN",
    "AICEFR_CREDIT_PACKS",
)


@pytest.mark.parametrize("name", ["core", "web"])
def test_the_metered_channel_reaches_core_and_web(name):
    """Set in .env, the IDPoint channel was never seen by the containers (31/10/2026)."""
    base = yaml.load(
        (ROOT / "docker-compose.yml").read_text(encoding="utf-8"), Loader=_ComposeLoader
    )
    env = _env(base["services"][name])
    for key in METERED:
        assert env.get(key, "").startswith("${" + key + ":-"), key
    example = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert all(f"\n{key}=" in example for key in METERED)
