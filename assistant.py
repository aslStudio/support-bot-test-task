"""Deterministic answers grounded in policy.json and the demo order database."""

import re
import sqlite3

from store import get_order, list_orders


HELP = (
    "Я отвечаю на вопросы о наушниках X1, доставке, возврате, браке и скидках. "
    "Команды: /data — регламент и состав демо-базы; /orders — тестовые заказы; "
    "/order 1001 — статус демо-заказа; /help — помощь. "
    "Можно также задать вопрос обычным сообщением."
)


def _delivery(policy: dict) -> str:
    item = policy["delivery"]
    return f"По регламенту доставка — {item['method']} {item['when']}, слот {item['window']}."


def _order_answer(order_id: str, policy: dict, connection: sqlite3.Connection) -> str:
    order = get_order(connection, order_id)
    if order is None:
        return (
            f"Заказ {order_id} не найден в демонстрационной базе. Его реальный статус мне неизвестен. "
            f"{_delivery(policy)} Чтобы узнать статус конкретного заказа, обратитесь к сотруднику магазина."
        )
    result = f"Демонстрационный заказ {order['id']}: {order['product']}, статус — {order['status']}."
    if order["delivery_note"]:
        result += f" {order['delivery_note']}"
    return result


def _day_number(text: str) -> int | None:
    match = re.search(r"\b(\d{1,3})(?:[-–](?:й|ый|ий|го|ом))?\s*(?:день|дня|дней|дне|днём)\b", text)
    return int(match.group(1)) if match else None


def answer(message: str, policy: dict, connection: sqlite3.Connection) -> str:
    raw = message.strip()
    text = raw.casefold().replace("ё", "е")
    command = text.split(maxsplit=1)[0].split("@", 1)[0] if text.startswith("/") else ""

    if command in ("/start", "/help"):
        return HELP
    if command == "/data":
        product = policy["product"]
        returns = policy["returns"]
        ids = ", ".join(row["id"] for row in list_orders(connection))
        return (
            "Регламент:\n"
            f"• {product['name']}: в наличии, {product['price_rub']:,} ₽.\n"
            f"• {_delivery(policy)}\n"
            f"• Возврат в течение {returns['days']} дней, на ту же карту; деньги приходят за "
            f"{returns['refund_in_business_days']} рабочих дня.\n"
            "• Вскрытый товар без брака тоже можно вернуть в течение 14 дней.\n"
            "• Брак принимаем на экспертизу; немедленный возврат денег не обещаем.\n"
            "• Скидок нет ни при каких условиях.\n\n"
            f"Демо-заказы в локальной базе: {ids}. Заказа 1842 в ней нет. "
            "Это тестовые записи, не реальные заказы. Для статуса: /order 1001."
        ).replace("2,490", "2 490")
    if command == "/orders":
        rows = list_orders(connection)
        return "Только демонстрационные заказы:\n" + "\n".join(
            f"• {row['id']} — {row['status']}" for row in rows
        )
    if command == "/order":
        match = re.fullmatch(r"/order(?:@\w+)?\s+(\d{1,20})", text)
        return _order_answer(match.group(1), policy, connection) if match else "Укажите номер: /order 1001."
    if command:
        return "Неизвестная команда. Напишите /help."

    # An order number is considered only next to the word "order". Other numbers
    # (a price, a percentage, or a return deadline) are never used as order IDs.
    order_match = re.search(r"\bзаказ(?:а|у|ом|е)?\s*(?:№\s*)?(\d{1,20})\b", text)
    if order_match:
        return _order_answer(order_match.group(1), policy, connection)
    if re.search(r"скид|дисконт|промокод|промо.код|уцен", text):
        return "По регламенту скидок нет ни при каких условиях."
    if re.search(r"брак|дефект|неисправ|слома|не работает", text):
        return "Товар с браком принимаем на экспертизу. Немедленный возврат денег обещать не могу."

    wants_return = bool(re.search(r"вернут|возврат|сдат|отказат", text))
    opened = bool(re.search(r"вскрыт|распакован|открыт|без упаковки", text))
    if wants_return or opened:
        days = _day_number(text)
        limit = policy["returns"]["days"]
        if days is not None and days > limit:
            return (
                f"По регламенту возврат возможен в течение {limit} дней, в том числе для вскрытого "
                "товара без брака. На указанный срок это правило уже не распространяется. "
                "Для решения вашего случая обратитесь к сотруднику магазина."
            )
        if opened:
            return (
                f"Вскрытый товар без брака можно вернуть в течение {limit} дней. "
                "Возврат — на ту же карту; деньги приходят за 3 рабочих дня."
            )
        return (
            f"Товар можно вернуть в течение {limit} дней. Возврат — на ту же карту; "
            "деньги приходят за 3 рабочих дня."
        )
    if re.search(r"достав|курьер|привез|когда придет заказ|где заказ|статус заказ", text):
        if "заказ" in text:
            return f"Укажите номер заказа. {_delivery(policy)} Статус конкретного заказа проверю только по демо-базе."
        return _delivery(policy)
    if re.search(r"наушник|\bx1\b|цен|стоит|наличи|купит|товар", text):
        item = policy["product"]
        return f"{item['name']} в наличии, цена — {item['price_rub']:,} ₽.".replace("2,490", "2 490")
    return "В регламенте и демонстрационной базе нет информации для ответа на этот вопрос. Обратитесь к сотруднику магазина."
