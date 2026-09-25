// Reads the backend API base URL from the environment.
//
// NEXT_PUBLIC_* variables are inlined into the client bundle at BUILD time
// by Next.js (see README.md for the implications of this in the Docker
// image built by this project's Dockerfile / docker-compose.yml).
export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
