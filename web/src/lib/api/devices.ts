import { apiFetch } from "../api-client";
import type { Device } from "../types";

export async function listDevices(): Promise<Device[]> {
  const data = await apiFetch<{ devices: Device[] }>("/devices");
  return data.devices;
}
