# IG Reels MP3 Bot

A Telegram bot + Flask server to convert Instagram Reels to MP3, ready for Render.com deployment.

## Quick Deploy on Render.com

1. **Push this repo to GitHub.**
2. **Create a new Web Service on [Render.com](https://render.com/):**
   - Connect your GitHub repo.
   - Render will auto-detect `render.yaml`.
   - Set the environment variable `TELEGRAM_BOT_TOKEN` (from BotFather).
   - Use the free plan or upgrade as needed.
3. **Deploy!**
   - The Flask server will start and the bot will run.
   - You may need to set up a webhook for Telegram if you want to receive messages (see below).

## Environment Variables
- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token (required)
- `PORT`: Render sets this automatically for Flask

## Notes
- The bot and Flask server run in the same process.
- If you want to use Telegram webhooks (recommended for production), you may need to update the bot code to use webhooks instead of polling.
- For simple use, polling works, but Render may sleep your service on the free plan.

## Requirements
See `requirements.txt`.

## .gitignore
See `.gitignore` for files not tracked in git.

---

**Questions?**
- See the code comments for more info.
- For advanced deployment (webhooks, custom domains), see the Render docs.
