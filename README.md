# Telegram Referral Bot

## Features
- Referral system with invite tracking
- Mandatory channel subscription check
- Prize distribution with single-use invite links
- Anti-cheat protection
- Admin panel with statistics
- Real-time user management

## Quick Deploy

### Option 1: Docker (Recommended)
```bash
# Clone and deploy
git clone <repository_url>
cd botlar
chmod +x deploy.sh
./deploy.sh
```

### Option 2: Manual Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Run bot
python concursbot.py
```

## Configuration
Edit `concursbot.py`:
- `TOKEN`: Your bot token from @BotFather
- `ADMIN_IDS`: List of admin user IDs
- `REQUIRED_INVITES`: Number of invites required for prize
- `CHANNELS`: List of mandatory channels
- `PRIZE_CHANNEL`: Prize channel ID

## Docker Commands
```bash
# Start bot
docker-compose up -d

# View logs
docker-compose logs -f bot

# Stop bot
docker-compose down

# Update bot
git pull
docker-compose build
docker-compose up -d
```

## Admin Commands
- `/admin` - Open admin panel
- `/add_admin <user_id>` - Add new admin
- `/remove_admin <user_id>` - Remove admin
- `/list_admins` - List all admins

## Environment Variables
Create `.env` file:
```
TOKEN=your_bot_token
ADMIN_IDS=123456789,987654321
```

## Support
For issues and support, contact the admin team.
