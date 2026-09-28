import { apiFetch } from "../api-client";
import type { Weather } from "../types";

export function getWeather(location: string): Promise<Weather> {
  return apiFetch<Weather>(`/weather?location=${encodeURIComponent(location)}`);
}
