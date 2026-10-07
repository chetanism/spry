import { describe, expect, test } from "vitest";
import { lend } from "./lend";
import { seed } from "../../test/seed";

const today = "2026-10-03";

describe("lend", () => {
  test("S-1/AC-1 lends a book to a member under the limit", async () => {
    const { kiran, prideAndPrejudice } = await seed();
    const result = await lend(kiran.id, prideAndPrejudice.id, today);
    expect(result.ok).toBe(true);
  });

  test("S-1/AC-1 refuses an unknown library card", async () => {
    const { prideAndPrejudice } = await seed();
    const result = await lend("no-such-member", prideAndPrejudice.id, today);
    expect(result).toEqual({ ok: false, error: "NoSuchMember" });
  });

  test("S-1/AC-2 sets the due date 14 days after the loan", async () => {
    const { kiran, prideAndPrejudice } = await seed();
    const result = await lend(kiran.id, prideAndPrejudice.id, today);
    expect(result.ok && result.value.dueOn).toBe("2026-10-17");
  });

  test("S-1/AC-3 refuses a book already on loan", async () => {
    const { kiran, sam, prideAndPrejudice } = await seed();
    await lend(kiran.id, prideAndPrejudice.id, today);
    const result = await lend(sam.id, prideAndPrejudice.id, today);
    expect(result).toEqual({ ok: false, error: "AlreadyOnLoan" });
  });
});
