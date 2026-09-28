"use client";

import { useState, type FormEvent } from "react";
import { ErrorMessage } from "@/components/ErrorMessage";
import { ApiError } from "@/lib/api-client";
import * as weatherApi from "@/lib/api/weather";
import type { Weather } from "@/lib/types";

function formatDay(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString("de-DE", { weekday: "short", day: "2-digit", month: "2-digit" });
  } catch {
    return iso;
  }
}

export function WeatherTab() {
  const [location, setLocation] = useState("");
  const [weather, setWeather] = useState<Weather | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSearch(e: FormEvent) {
    e.preventDefault();
    if (!location.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const result = await weatherApi.getWeather(location.trim());
      setWeather(result);
    } catch (err) {
      setWeather(null);
      setError(err instanceof ApiError ? err.message : "Wetter konnte nicht geladen werden.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-xl">
      <p className="mb-4 text-sm text-zinc-500">
        Wetterabfrage über Open-Meteo (keine Anmeldung nötig) — auch per Chat/Sprache abrufbar
        (&bdquo;Wie wird das Wetter in Hamburg?&ldquo;).
      </p>

      <form onSubmit={handleSearch} className="mb-4 flex gap-2">
        <input
          type="text"
          placeholder="Ort, z.B. 'Berlin'"
          value={location}
          onChange={(e) => setLocation(e.target.value)}
          className="flex-1 rounded-md border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
        />
        <button
          type="submit"
          disabled={loading || !location.trim()}
          className="rounded-md bg-zinc-900 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-zinc-700 disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900"
        >
          {loading ? "Lade..." : "Abfragen"}
        </button>
      </form>

      <ErrorMessage message={error} />

      {weather && (
        <div className="rounded-lg border border-zinc-200 p-4 dark:border-zinc-800">
          <p className="mb-1 text-lg font-medium text-zinc-900 dark:text-zinc-100">
            {weather.location}
            {weather.country ? `, ${weather.country}` : ""}
          </p>
          <p className="mb-4 text-sm text-zinc-500">
            {weather.current_condition} · {weather.current_temperature.toFixed(1)}°C · Wind{" "}
            {weather.current_wind_speed.toFixed(0)} km/h
          </p>
          <div className="flex gap-3">
            {weather.daily.map((day) => (
              <div key={day.date} className="flex-1 rounded-md border border-zinc-200 p-2 text-center text-xs dark:border-zinc-800">
                <p className="mb-1 font-medium text-zinc-700 dark:text-zinc-300">{formatDay(day.date)}</p>
                <p className="text-zinc-500">{day.condition}</p>
                <p className="mt-1 text-zinc-900 dark:text-zinc-100">
                  {day.temp_max.toFixed(0)}° / {day.temp_min.toFixed(0)}°
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
