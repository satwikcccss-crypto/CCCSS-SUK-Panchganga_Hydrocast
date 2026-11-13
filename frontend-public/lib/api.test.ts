import { api, clearApiCache } from "../lib/api";

const mockFetch = jest.fn();
(global as any).fetch = mockFetch;

describe("API client - no hardcoded fallbacks", () => {
  beforeEach(() => {
    mockFetch.mockReset();
    mockFetch.mockResolvedValue({
      ok: true,
      json: jest.fn().mockResolvedValue({}),
    });
    clearApiCache();
  });

  describe("status", () => {
    it("returns null when API returns null data", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: jest.fn().mockResolvedValue(null),
      });

      const result = await api.status();
      expect(result).toBeNull();
    });
  });

  describe("runoffSummary", () => {
    it("returns null when no data is available", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: jest.fn().mockResolvedValue(null),
      });

      const result = await api.runoffSummary();
      expect(result).toBeNull();
    });
  });

  describe("bridgeShivaji", () => {
    it("returns null when no data is available", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: jest.fn().mockResolvedValue(null),
      });

      const result = await api.bridgeShivaji();
      expect(result).toBeNull();
    });
  });

  describe("bridgeRajaram", () => {
    it("returns null when no data is available", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: jest.fn().mockResolvedValue(null),
      });

      const result = await api.bridgeRajaram();
      expect(result).toBeNull();
    });
  });
});
