import Inty from "inty";
import dotenv from "dotenv";

// Load .env file
dotenv.config();

const client = new Inty({
  apiKey: process.env["INTY_API_KEY"], // This is the default and can be omitted
  baseURL: "http://localhost:8000",
});

const agentsResponse = await client.api.v1.ai.agents.list();
console.log("Agents:", agentsResponse);

const guestResponse = await client.api.v1.auth.createGuest({
  device_id: "example-device-id",
  system_language: "en",
});

console.log("Guest:", guestResponse);
