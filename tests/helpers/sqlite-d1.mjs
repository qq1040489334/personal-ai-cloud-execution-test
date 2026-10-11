import { DatabaseSync } from "node:sqlite";

// Isolated SQLite transport, NOT a Cloudflare D1 emulator or a real-D1 receipt.
// Deferred prepare matches D1 batches that create a table then use that table.
export function sqliteD1(path = ":memory:") {
  const sqlite = new DatabaseSync(path);
  sqlite.exec("PRAGMA foreign_keys = ON");
  const db = { sqlite, failBefore: null, prepare(sql) {
    const statement = { sql, args: [], bind(...args) { return { ...statement, args }; },
      async first() { return sqlite.prepare(this.sql).get(...this.args) ?? null; },
      async all() { return { results: sqlite.prepare(this.sql).all(...this.args) }; },
      async run() {
        const s = sqlite.prepare(this.sql);
        if (s.columns().length) return { results: s.all(...this.args), meta: { changes: 0 }, success: true };
        const result = s.run(...this.args);
        return { success: true, meta: { changes: Number(result.changes) } };
      } };
    return statement;
  }, async batch(statements) {
    sqlite.exec("BEGIN IMMEDIATE");
    try {
      const results = [];
      for (const s of statements) {
        if (db.failBefore?.(s.sql)) throw new Error("synthetic batch failure");
        results.push(await s.run());
      }
      sqlite.exec("COMMIT");
      return results;
    } catch (error) { sqlite.exec("ROLLBACK"); throw error; }
  } };
  return db;
}
