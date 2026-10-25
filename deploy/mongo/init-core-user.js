// One database, and one user for the core service (D044, D048).
//
// The core service connects as its own user, which may read and write its
// databases and nothing else -- `aicefr`, and the learning part's and the
// metering ledger's (D051: a database per service); the root user stays for backups. Run once,
// by the mongo image, when the data volume is first created. The password comes
// from the environment.
const password = process.env.CORE_DB_PASSWORD;
if (!password) {
  throw new Error("init-core-user: CORE_DB_PASSWORD is not set");
}
db.getSiblingDB("aicefr").createUser({
  user: "core",
  pwd: password,
  roles: [
    { role: "readWrite", db: "aicefr" },
    { role: "readWrite", db: "aicefr_learning" },
    { role: "readWrite", db: "aicefr_metering" },
  ],
});
