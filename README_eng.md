💈 Telegram Bot for Service Booking (Barbershop)

Demo project: a functional Telegram bot for online client booking with selection of service, master, available date, and time.

The bot automatically checks busy slots, stores data in an SQLite database, and sends notifications to the administrator.

Features

· Step-by-step booking wizard: interactive selection of service, master, date, and available time via Inline keyboards;
· Double-booking protection: real-time check of master availability in the database;
· Time filtering: automatic hiding of past hours for same-day bookings;
· Client personal account ("My bookings"): view upcoming visits and cancel a booking;
· Administrator notifications: instant Telegram alerts when new bookings are created;
· Information section: convenient display of the price list, list of masters, and contacts.

Database and Data Storage

· a lightweight local SQLite database (barbershop.db) is used;
· the database structure is created automatically on first launch;
· only booking data is stored (user ID, name, master, service, date, and time).

Stack

· Python 3.10+
· aiogram 3.x (asynchronous framework for Telegram bots)
· SQLite3 (built-in relational DB)
· python-dotenv, logging

Project Structure

```
project/
├── main_2.py          # main bot code and booking logic
├── requirements.txt   # project dependencies
├── .env.example       # example configuration file
└── README.md          # documentation
```

Installation and Launch

1. Get a Telegram bot token: message @BotFather, send the /newbot command.
2. Find out your Telegram ID (for receiving notifications): message @userinfobot.
3. Install dependencies (a virtual environment is recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate        # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```
4. Create a .env file based on the example and fill in the data:
   ```bash
   cp .env.example .env            # Windows: copy .env.example .env
   ```
   ```env
   telegram_bot_token_here=your_bot_token
   ADMIN_ID=your_telegram_id
   ```
5. Run the bot:
   ```bash
   python main_2.py
   ```
6. Open the bot in Telegram, send /start or /menu to go to booking.

Configuration

What Where Description
List of services SERVICES dictionary in main_2.py Name, price in ₸/₽, and duration
List of masters MASTERS dictionary in main_2.py Names and specializations of masters
Time slots TIME_SLOTS list in main_2.py Available hours for booking (e.g., ["10:00", "11:00"])
Booking depth DAYS_AHEAD variable How many days ahead booking is allowed (default 7)
Establishment contacts SHOP_NAME, ADDRESS, PHONE constants Name, address, and contacts for the menu

Possible Issues

· Booking is not saved / database error: make sure the script has write permissions for files in the project directory to create barbershop.db.
· Administrator does not receive notifications: check that a valid numeric user ID is specified in .env (not a nickname with @), and that you have started the bot from your account.
· "This time was just taken": the protection against simultaneous booking of the same slot by multiple users has triggered.

Security

Do not publish the .env file or the barbershop.db database file publicly. Add .env and *.db to the .gitignore file.

---

💼 To order a bot like this for any tasks with full support, message us on Telegram: @dark_baga7
