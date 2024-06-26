import json
from os import path
import re
import time
import aiohttp
from hoshino import Service

sv_help = '''
汇率
[汇率] 查看汇率
[汇率+货币] 查看汇率
[汇率+数额+货币] 查看汇率
[汇率收藏+货币] 收藏货币
[汇率取消收藏+货币] 取消收藏货币
'''.strip()

sv = Service(
    name="汇率",  # 功能名
    visible=True,  # 可见性
    enable_on_default=True,  # 默认启用
    bundle="工具",  # 分组归类
    help_=sv_help,  # 帮助说明
)

def file_path(file_name):
    return path.join(path.dirname(__file__), file_name)

api_url = 'https://api.exchange-rate.yuudi.dev/exchange-rate.json'
alias = {}
readable = {}
with open(file_path('alias.json'), 'r') as f:
    alias = json.load(f)
with open(file_path('currencies.csv'), 'r') as f:
    currencies = f.read().split('\n')
    for currency in currencies:
        alias[currency[3]] = currency[0]
        readable[currency[0]] = currency[3]

rate = {
    'updated': 0,
    'rates': {},
}
saved = [
    'USD',
    'CNY',
    'JPY',
]

if path.exists(file_path('data/rate.json')):
    with open(file_path('data/rate.json'), 'r') as f:
        rate = json.load(f)
if path.exists(file_path('data/saved.json')):
    with open(file_path('data/saved.json'), 'r') as f:
        saved = json.load(f)

def save_rate():
    with open(file_path('data/rate.json'), 'w') as f:
        json.dump(rate, f)
def save_saved():
    with open(file_path('data/saved.json'), 'w') as f:
        json.dump(saved, f)

@sv.on_prefix("汇率")
async def _(bot, event):
    query = event.raw_message
    if query.startswith('汇率收藏'):
        currency_name = query[4:].strip()
        if not currency_name:
            await bot.send(event, '汇率收藏+货币')
            return
        currency = alias.get(currency_name)
        if currency is None:
            await bot.send(event, '不支持的货币')
            return
        if not currency in rate:
            await bot.send(event, '无数据：' + readable[currency])
            return
        if currency not in saved:
            saved.append(currency)
            save_saved()
        await bot.send(event, f'{currency} 已收藏')
        return
    if query.startswith('汇率取消收藏'):
        currency_name = query[6:].strip()
        if not currency_name:
            await bot.send(event, '汇率取消收藏+货币')
            return
        currency = alias.get(currency_name)
        if currency is None:
            await bot.send(event, '不支持的货币')
            return
        if currency not in saved:
            await bot.send(event, '未收藏：' + readable[currency])
            return
        saved.remove(currency)
        save_saved()
        await bot.send(event, f'{currency} 已取消收藏')
        return
    if query.startswith('汇率'):
        query = query[2:].strip()
        if not query:
            await bot.send(event, await get_message('USD', 100))
            return
        value = 100
        query_value = re.match(r'^(\d+(?:\.\d{1,2}))', query)
        if query_value:
            value = float(query_value.group(1))
            query = query[query_value.end():].strip()
        currency_name = query
        if not currency_name:
            await bot.send(event, '汇率\n汇率+货币\n汇率+数额+货币')
            return
        currency = alias.get(currency_name)
        if currency is None:
            await bot.send(event, '不支持的货币')
            return
        if currency not in rate:
            await bot.send(event, '无数据：' + readable[currency])
            return
        await bot.send(event, await get_message(currency, value))

async def update_rate():
    now_ts = int(time.time())
    updated = rate['updated']
    if now_ts - updated < 24 * 60 * 60:
        return
    async with aiohttp.ClientSession() as session:
        async with session.get(api_url) as resp:
            if resp.status != 200:
                return
            data = await resp.json()
            rate = data
            save_rate()

async def get_message(currency, value):
    await update_rate()
    rates = rate['rates']
    core_value = value / rates[currency]
    message = f'{value} {readable[currency]} 等于\n'
    for c in saved:
        v = core_value * rates[c]
        message += f'{v:.4f} {readable[c]}\n'
    return message
