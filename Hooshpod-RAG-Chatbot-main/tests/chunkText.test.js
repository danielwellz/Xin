import { describe, expect, it } from "vitest";
import { chunkText } from "../src/services/chat.service.js";
describe("chunkText", () => {
    it("returns empty array for blank input", () => {
        expect(chunkText("   ", 200)).toEqual([]);
    });
    it("splits paragraphs and respects chunk size", () => {
        const text = [
            "Paragraph one has enough words to be split across multiple chunks if the chunk size is small.",
            "Paragraph two is short.",
            "Paragraph three is extremely long and should be broken into multiple pieces because its length exceeds the limit we pass in for the size parameter. ".repeat(5),
        ].join("\n\n");
        const chunks = chunkText(text, 80);
        expect(chunks.length).toBeGreaterThan(3);
        expect(chunks[0]).toContain("Paragraph one");
        expect(chunks.some((chunk) => chunk.includes("Paragraph two"))).toBe(true);
        expect(chunks.some((chunk) => chunk.includes("Paragraph three"))).toBe(true);
        expect(chunks.every((chunk) => chunk.length <= 80)).toBe(true);
    });
});
