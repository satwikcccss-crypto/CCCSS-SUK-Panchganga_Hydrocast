import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";

// Utility to fetch latest pipeline state
function getLatestData() {
  const candidates = [
    path.join(process.cwd(), "public", "data", "latest_pipeline_state.json"),
    path.join(process.cwd(), "data", "openmeteo_dss", "latest_pipeline_state.json"),
  ];

  for (const file of candidates) {
    try {
      if (fs.existsSync(file)) {
        return JSON.parse(fs.readFileSync(file, "utf-8"));
      }
    } catch (e) {
      console.error(`Error reading ${file}:`, e);
    }
  }
  return null;
}

const TELEGRAM_BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;

async function sendMessage(chatId: number, text: string) {
  if (!TELEGRAM_BOT_TOKEN) {
    console.error("Missing TELEGRAM_BOT_TOKEN");
    return;
  }
  const url = `https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage`;
  try {
    await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        chat_id: chatId,
        text: text,
        parse_mode: "HTML",
        disable_web_page_preview: true,
      }),
    });
  } catch (error) {
    console.error("Failed to send Telegram message:", error);
  }
}

export async function POST(req: Request) {
  try {
    const body = await req.json();

    // Respond immediately if not a text message
    if (!body?.message?.text) {
      return NextResponse.json({ ok: true });
    }

    const chatId = body.message.chat.id;
    const text = body.message.text.trim();
    const data = getLatestData();

    if (text.startsWith("/start") || text.startsWith("/help")) {
      const msg = `🌊 <b>HydroCast Flood Intelligence Bot</b>\n\n` +
                  `Available commands:\n` +
                  `/status - System health & latest forecast cycle\n` +
                  `/stage - Current water levels and peak stages\n` +
                  `/alerts - Active warning and danger alerts\n` +
                  `/bulletin - Latest CWC flood bulletin`;
      await sendMessage(chatId, msg);
    } 
    else if (text.startsWith("/status")) {
      const cycle = data?.cycle_id || "Unknown";
      const time = data?.summary?.peak_time || new Date().toISOString();
      const msg = `✅ <b>HydroCast System Status</b>: OPERATIONAL\n` +
                  `Server Time: ${new Date().toISOString()}\n` +
                  `Latest Cycle: ${cycle}\n` +
                  `Forecasting Interval: 6-hourly automated cycles (00z, 06z, 12z, 18z)`;
      await sendMessage(chatId, msg);
    } 
    else if (text.startsWith("/stage")) {
      if (!data?.summary?.bridges) {
        await sendMessage(chatId, "ℹ️ No active stage forecasts available.");
      } else {
        const shivaji = data.summary.bridges.shivaji;
        const rajaram = data.summary.bridges.rajaram;
        
        let msg = `📊 <b>Current Bridge Stages</b>\n━━━━━━━━━━━━━━━━━━━━━━\n`;
        if (shivaji) {
          msg += `📍 <b>${shivaji.site_name}</b>\n`;
          msg += `Current: ${shivaji.current_stage_m?.toFixed(2)} m\n`;
          msg += `Peak: <code>${shivaji.peak_stage_m?.toFixed(2)} m</code> at ${shivaji.peak_arrival_time || 'N/A'}\n\n`;
        }
        if (rajaram) {
          msg += `📍 <b>${rajaram.site_name}</b>\n`;
          msg += `Current: ${rajaram.current_stage_m?.toFixed(2)} m\n`;
          msg += `Peak: <code>${rajaram.peak_stage_m?.toFixed(2)} m</code> at ${rajaram.peak_arrival_time || 'N/A'}\n\n`;
        }
        await sendMessage(chatId, msg);
      }
    } 
    else if (text.startsWith("/alerts") || text.startsWith("/bulletin")) {
      // In a real scenario, you would filter by alert_level === "WARNING" | "DANGER"
      if (!data?.summary?.bridges) {
        await sendMessage(chatId, "✅ No active flood warnings.");
      } else {
        const bridges = Object.values(data.summary.bridges) as any[];
        const alerts = bridges.filter(b => b.alert_level !== "NORMAL");
        
        if (alerts.length === 0) {
          await sendMessage(chatId, "✅ No active flood warnings.");
        } else {
          let msg = `🚨 <b>Active Flood Alerts</b>\n━━━━━━━━━━━━━━━━━━━━━━\n`;
          for (const a of alerts) {
            msg += `🔴 <b>[${a.alert_level}] ${a.site_name}</b>\n`;
            msg += `Peak: ${a.peak_stage_m?.toFixed(2)} m (Arrival: ${a.peak_arrival_time})\n\n`;
          }
          await sendMessage(chatId, msg);
        }
      }
    } 
    else {
      await sendMessage(chatId, "I don't understand that command. Please type /help to see available options.");
    }

    return NextResponse.json({ ok: true });
  } catch (error) {
    console.error("Telegram Webhook Error:", error);
    return NextResponse.json({ ok: false, error: "Internal Server Error" }, { status: 500 });
  }
}
