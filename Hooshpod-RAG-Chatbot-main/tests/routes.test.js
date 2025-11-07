import request from "supertest";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
const chatWithUserMock = vi.fn();
const getHistoryByUserMock = vi.fn();
vi.mock("../src/services/chat.service.js", () => ({
    chatWithUser: chatWithUserMock,
    getHistoryByUser: getHistoryByUserMock,
}));
let app;
beforeEach(async () => {
    chatWithUserMock.mockReset();
    getHistoryByUserMock.mockReset();
    // Re-import app after resetting mocks to ensure routers use latest spies.
    ({ default: app } = await import("../src/app.js"));
});
afterEach(() => {
    vi.resetModules();
});
describe("POST /chat", () => {
    it("returns 200 with payload from chat service", async () => {
        chatWithUserMock.mockResolvedValue({
            response: "Hello!",
            cached: false,
            timestamp: "2025-01-01T00:00:00.000Z",
            sessionId: "session-123",
        });
        const res = await request(app)
            .post("/chat")
            .send({ message: "Hi there", userId: "user-1" })
            .expect(200);
        expect(res.body).toEqual({
            response: "Hello!",
            cached: false,
            timestamp: "2025-01-01T00:00:00.000Z",
            sessionId: "session-123",
        });
        expect(chatWithUserMock).toHaveBeenCalledWith({
            message: "Hi there",
            userId: "user-1",
            sessionId: undefined,
        });
    });
    it("returns 400 on validation error", async () => {
        const res = await request(app)
            .post("/chat")
            .send({ message: "", userId: "" })
            .expect(400);
        expect(res.body.message).toEqual("Invalid request body");
        expect(chatWithUserMock).not.toHaveBeenCalled();
    });
});
describe("GET /history/:userId", () => {
    it("returns history for given user", async () => {
        getHistoryByUserMock.mockResolvedValue([
            {
                userId: "user-1",
                sessionId: "session-1",
                message: "Question?",
                response: "Answer!",
                cached: false,
                createdAt: new Date("2025-01-01T00:00:00Z"),
                updatedAt: new Date("2025-01-01T00:00:00Z"),
            },
        ]);
        const res = await request(app)
            .get("/history/user-1?limit=5&page=2")
            .expect(200);
        expect(res.body).toMatchObject({
            userId: "user-1",
            limit: 5,
            page: 2,
        });
        expect(Array.isArray(res.body.history)).toBe(true);
        expect(getHistoryByUserMock).toHaveBeenCalledWith("user-1", 5, 2);
    });
    it("returns 400 for invalid query params", async () => {
        const res = await request(app)
            .get("/history/user-1?limit=-1")
            .expect(400);
        expect(res.body.message).toEqual("Invalid query parameters");
        expect(getHistoryByUserMock).not.toHaveBeenCalled();
    });
});
