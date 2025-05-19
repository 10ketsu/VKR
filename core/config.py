
import os
import dotenv
import pymorphy2
from aiogram import Dispatcher, Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from groq import AsyncGroq

dotenv.load_dotenv()
bot = Bot(os.environ.get('TOKEN'), default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = RedisStorage.from_url(os.environ.get('REDIS_URL'))
dp = Dispatcher(storage=storage)
morph = pymorphy2.MorphAnalyzer()
groq_client = AsyncGroq(api_key=os.environ.get('GROQ_API_KEY'))
