from flask import Flask, jsonify, render_template, request

from pickwise.utils.entity_detection import detect_hero, detect_item
from pickwise.utils.intent_classifier import (
    IntentClassifier,
    rule_based_intent,
    is_item_info_question,
    is_self_intro_question,
    is_greeting,
    is_dota_related,
)
from pickwise.utils.text_preprocessing import normalize_user_input
from pickwise.utils.triggers import match_intent_by_triggers
from pickwise.utils.opendota_client import OpenDotaError
from pickwise.utils.response_generator import (
    generate_hero_build_response,
    generate_hero_counters_response,
    generate_hero_counter_items_response,
    generate_item_counter_response,
    generate_item_info_response,
    generate_generic_strategy_response,
    generate_self_intro_response,
)


app = Flask(__name__)
_intent_classifier = IntentClassifier()


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json(force=True, silent=True) or {}
    raw_question = (data.get("question") or "").strip()
    question = normalize_user_input(raw_question)
    if not question:
        return jsonify({"answer": "Please ask a question about heroes, items, or strategy."}), 400

    # Warm greeting: respond with a friendly self-introduction on short salutations.
    if is_greeting(question):
        answer = generate_self_intro_response()
        return jsonify({"answer": answer, "intent": "self_intro_greeting", "confidence": 1.0})

    # Self-intro priority: when user asks about the bot, always respond with introduction
    if is_self_intro_question(question):
        answer = generate_self_intro_response()
        return jsonify({"answer": answer, "intent": "self_intro", "confidence": 1.0})

    # Politely decline non-Dota questions.
    if not is_dota_related(question):
        answer = (
            "I'm sorry! I'm PickWise, and I'm only designed to give advice about Dota 2, "
            "like hero counters, item builds, item counters, and strategy tips."
        )
        return jsonify({"answer": answer, "intent": "out_of_scope", "confidence": 1.0})

    try:
        hero = detect_hero(question)
        item = detect_item(question)
    except OpenDotaError:
        return jsonify(
            {
                "answer": (
                    "I attempted to retrieve data from the OpenDota API but the service is currently unavailable. "
                    "Please try again shortly."
                )
            }
        )

    # Item detection priority: if user message contains an item and asks what it is, always answer with item info
    if item and is_item_info_question(question, item):
        answer = generate_item_info_response(item)
        return jsonify({"answer": answer, "intent": "item_info", "confidence": 1.0})

    # Trigger-based intent: if user phrasing matches known triggers, use that intent (no ML needed)
    trigger_intent = match_intent_by_triggers(question, hero is not None, item is not None)
    if trigger_intent == "counter_hero_items" and hero:
        answer = generate_hero_counter_items_response(hero)
        return jsonify({"answer": answer, "intent": "counter_hero_items", "confidence": 1.0})
    if trigger_intent == "counter_heroes" and hero:
        answer = generate_hero_counters_response(hero)
        return jsonify({"answer": answer, "intent": "counter_heroes", "confidence": 1.0})
    if trigger_intent == "hero_build":
        answer = generate_hero_build_response(hero)
        return jsonify({"answer": answer, "intent": "hero_build", "confidence": 1.0})
    if trigger_intent == "counter_items" and item:
        answer = generate_item_counter_response(item)
        return jsonify({"answer": answer, "intent": "counter_items", "confidence": 1.0})
    if trigger_intent == "item_info" and item:
        answer = generate_item_info_response(item)
        return jsonify({"answer": answer, "intent": "item_info", "confidence": 1.0})
    if trigger_intent == "general_strategy":
        answer = generate_generic_strategy_response(hero, question)
        return jsonify({"answer": answer, "intent": "general_strategy", "confidence": 1.0})

    # ML model intent (when triggers did not match)
    try:
        intent_result = _intent_classifier.predict(question)
        intent = intent_result.intent
        confidence = intent_result.confidence
    except FileNotFoundError:
        intent = rule_based_intent(question, hero, item) or "general_strategy"
        confidence = 0.0

    if intent == "general_strategy" or confidence < 0.45:
        rb_intent = rule_based_intent(question, hero, item)
        if rb_intent is not None:
            intent = rb_intent

    if intent == "self_intro":
        answer = generate_self_intro_response()
    elif intent == "counter_hero_items" and hero:
        answer = generate_hero_counter_items_response(hero)
    elif intent == "counter_heroes" and hero:
        answer = generate_hero_counters_response(hero)
    elif intent == "hero_build":
        answer = generate_hero_build_response(hero)
    elif intent == "counter_items" and item:
        answer = generate_item_counter_response(item)
    elif (intent in ("item_info", "item_description")) and item:
        answer = generate_item_info_response(item)
    else:
        answer = generate_generic_strategy_response(hero, question)

    return jsonify({"answer": answer, "intent": intent, "confidence": confidence})


@app.route("/chat", methods=["POST"])
def chat():
    """
    Chat endpoint for the modern frontend. Accepts JSON:
        { "message": "user text" }
    and returns:
        { "answer": "...", "intent": "...", "confidence": 0.0-1.0 }
    """
    data = request.get_json(force=True, silent=True) or {}
    raw_text = (data.get("message") or data.get("question") or "").strip()
    text = normalize_user_input(raw_text)
    if not text:
        return jsonify({"answer": "Please provide a question for PickWise to answer."}), 400

    if is_greeting(text):
        answer = generate_self_intro_response()
        return jsonify({"answer": answer, "intent": "self_intro_greeting", "confidence": 1.0})

    if is_self_intro_question(text):
        answer = generate_self_intro_response()
        return jsonify({"answer": answer, "intent": "self_intro", "confidence": 1.0})

    if not is_dota_related(text):
        answer = (
            "I'm sorry! I'm PickWise, and I'm only designed to give advice about Dota 2, "
            "like hero counters, item builds, item counters, and strategy tips."
        )
        return jsonify({"answer": answer, "intent": "out_of_scope", "confidence": 1.0})

    try:
        hero = detect_hero(text)
        item = detect_item(text)
    except OpenDotaError:
        return jsonify(
            {
                "answer": (
                    "I attempted to retrieve data from the OpenDota API but the service is currently unavailable. "
                    "Please try again shortly."
                )
            }
        )

    if item and is_item_info_question(text, item):
        answer = generate_item_info_response(item)
        return jsonify({"answer": answer, "intent": "item_info", "confidence": 1.0})

    trigger_intent = match_intent_by_triggers(text, hero is not None, item is not None)
    if trigger_intent == "counter_hero_items" and hero:
        answer = generate_hero_counter_items_response(hero)
        return jsonify({"answer": answer, "intent": "counter_hero_items", "confidence": 1.0})
    if trigger_intent == "counter_heroes" and hero:
        answer = generate_hero_counters_response(hero)
        return jsonify({"answer": answer, "intent": "counter_heroes", "confidence": 1.0})
    if trigger_intent == "hero_build":
        answer = generate_hero_build_response(hero)
        return jsonify({"answer": answer, "intent": "hero_build", "confidence": 1.0})
    if trigger_intent == "counter_items" and item:
        answer = generate_item_counter_response(item)
        return jsonify({"answer": answer, "intent": "counter_items", "confidence": 1.0})
    if trigger_intent == "item_info" and item:
        answer = generate_item_info_response(item)
        return jsonify({"answer": answer, "intent": "item_info", "confidence": 1.0})
    if trigger_intent == "general_strategy":
        answer = generate_generic_strategy_response(hero, text)
        return jsonify({"answer": answer, "intent": "general_strategy", "confidence": 1.0})

    try:
        intent_result = _intent_classifier.predict(text)
        intent = intent_result.intent
        confidence = intent_result.confidence
    except FileNotFoundError:
        intent = rule_based_intent(text, hero, item) or "general_strategy"
        confidence = 0.0

    if intent == "general_strategy" or confidence < 0.45:
        rb_intent = rule_based_intent(text, hero, item)
        if rb_intent is not None:
            intent = rb_intent

    if intent == "self_intro":
        answer = generate_self_intro_response()
    elif intent == "counter_hero_items" and hero:
        answer = generate_hero_counter_items_response(hero)
    elif intent == "counter_heroes" and hero:
        answer = generate_hero_counters_response(hero)
    elif intent == "hero_build":
        answer = generate_hero_build_response(hero)
    elif intent == "counter_items" and item:
        answer = generate_item_counter_response(item)
    elif (intent in ("item_info", "item_description")) and item:
        answer = generate_item_info_response(item)
    else:
        answer = generate_generic_strategy_response(hero, text)

    return jsonify({"answer": answer, "intent": intent, "confidence": confidence})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

