from flask import Blueprint, request

blp = Blueprint("telegram", __name__)


@blp.route("")
def telegram_webhook():
    print(request.json)
    return "", 200
