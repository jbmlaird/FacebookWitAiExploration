from messengerbot import MessengerClient, messages, attachments, templates, elements
from flask import Flask, request
from wit import Wit
import pprint
import requests
import datetime

import re

pp = pprint.PrettyPrinter(indent=4)

app = Flask(__name__)

FB_ACCESS_TOKEN = "{removed}"
WIT_SERVER_TOKEN = "{removed}"

messenger = MessengerClient(access_token=FB_ACCESS_TOKEN)

user_conversations = []

# Wit.ai modified to pick up locations
# stationNames = "liverpool", "birmingham", "manchester", "oxford", "london"

@app.route('/incoming', methods=['GET'])
def facebook_get():
    return request.args['hub.challenge']


def first_entity_value(entities, entity):
    if entity not in entities:
        print("Returned None")
        return None
    val = entities[entity][0]['value']
    if not val:
        return None
    return val['value'] if isinstance(val, dict) else val


def ask_for_confirmation(session_id, context):
    if 'ticket_type' not in context:
        send_single_or_return_template(session_id)
    else:
        send_yes_no_template(session_id)
    return context


def ask_location_nature(session_id, context):
    recipient = messages.Recipient(session_id)
    home_button = elements.PostbackButton(
        title="Home",
        payload="saveLocationAsHome"
    )
    university_button = elements.PostbackButton(
        title="University",
        payload="saveLocationAsUniversity"
    )
    other_button = elements.PostbackButton(
        title="Other",
        payload="saveLocationAsOther"
    )
    if 'location:origin' in context:
        template = templates.ButtonTemplate(
            text="What's the nature of " + str(context['location:origin']) + "?",
            buttons=[
                home_button, university_button, other_button
            ]
        )
    else:
        template = templates.ButtonTemplate(
            text="What's the nature of " + str(context['location:destination']) + "?",
            buttons=[
                home_button, university_button, other_button
            ]
        )
    attachment = attachments.TemplateAttachment(template=template)
    message = messages.Message(attachment=attachment)
    request = messages.MessageRequest(recipient, message)
    messenger.send(request)
    print("Ask Location Nature final context: " + str(context))
    return context


def ask_to_memorize_location(user_id, context):
    recipient = messages.Recipient(user_id)
    location_save_yes_button = elements.PostbackButton(
        title="Yes",
        payload="saveLocationConfirmedYes"
    )
    location_save_no_button = elements.PostbackButton(
        title="No",
        payload="saveLocationConfirmedNo"
    )
    template = templates.ButtonTemplate(
        text="Would you like to save this location?",
        buttons=[
            location_save_yes_button, location_save_no_button
        ]
    )
    attachment = attachments.TemplateAttachment(template=template)
    message = messages.Message(attachment=attachment)
    request = messages.MessageRequest(recipient, message)
    messenger.send(request)
    return context


def memorize_location(user_id, context, saveAs):
    global user_conversations
    user_dictionary = next(item for item in user_conversations if item["recipient"]['id'] == user_id)
    print("Memorize location context: " + str(context))
    if 'location:origin' not in context:
        if saveAs == "home":
            user_dictionary['savedHome'] = context['location:destination']
        elif saveAs == "university":
            user_dictionary['savedUniversity'] = context['location:destination']
        elif saveAs == "other":
            user_dictionary['savedUniversity'] = context['location:destination']
        if 'savedInformation' in user_dictionary:
            if user_dictionary['savedHome'] != "" or user_dictionary['savedUniversity'] != "":
                ask_user_for_origin(user_id, user_dictionary['savedHome'], user_dictionary['savedUniversity'])
        else:
            send_text_message(user_id, "Where are you going from?")
    else:
        if saveAs == "home":
            user_dictionary['savedHome'] = context['location:origin']
        elif saveAs == "university":
            user_dictionary['savedUniversity'] = context['location:origin']
        elif saveAs == "other":
            user_dictionary['savedUniversity'] = context['location:origin']
        send_text_message(user_id, "What date and time would you like to depart? Please use format: 5th July 5pm")
    return context


def display_sample_ticket(user_id, context):
    print("Display sample tickets")
    data = { "recipient":{
        "id":user_id
      },
      "message":{
        "attachment":{
          "type":"template",
          "payload":{
            "template_type":"generic",
            "elements":[
              {
                "title":"Ticket One",
                "buttons":[
                  {
                    "type":"postback",
                    "title":"Buy this ticket",
                    "payload":"ticketSelected"
                  },
                    {
                        "type": "postback",
                        "title": "Change ticket prefs",
                        "payload": "changePreferences"
                    },
                    {
                        "type": "postback",
                        "title": "Change travel time",
                        "payload": "changeDates"
                    }
                ]
              },
              {
                "title":"Ticket Two",
                "buttons":[
                  {
                    "type":"postback",
                    "title":"Buy this ticket",
                    "payload":"ticketSelected"
                  },
                    {
                        "type": "postback",
                        "title": "Change ticket prefs",
                        "payload": "changePreferences"
                    },
                    {
                        "type": "postback",
                        "title": "Change travel time",
                        "payload": "changeDates"
                    }
                ]
              },
                {
                    "title": "Ticket Three",
                    "buttons": [
                        {
                            "type": "postback",
                            "title": "Buy this ticket",
                            "payload": "ticketSelected"
                        },
                    {
                        "type": "postback",
                        "title": "Change ticket prefs",
                        "payload": "changePreferences"
                    },
                    {
                        "type": "postback",
                        "title": "Change travel time",
                        "payload": "changeDates"
                    }
                    ]
                }
            ]
          }
        }
      },
    }
    response = requests.post("https://graph.facebook.com/v2.6/me/messages?access_token=" + FB_ACCESS_TOKEN, json=data)
    print("Response: " + str(response.content))
    return context


def save_ticket_preferences(user_id, context, decision):
    global user_conversations
    if str(decision) == 'yes':
        user_dictionary = next(item for item in user_conversations if item["recipient"]['id'] == user_id)
        user_dictionary['ticketPreference'] = user_dictionary['context']['ticketPreference']
    send_text_message(user_id, "This is where I would search for tickets.")
    display_sample_ticket(user_id, context)
    return context


def set_ticket_preferences(user_id, context, decision):
    global user_conversations
    user_dictionary = next(item for item in user_conversations if item["recipient"]['id'] == user_id)
    user_dictionary['context']['ticketPreference'] = decision
    ask_to_save_ticket_preferences(user_id, context)
    return context


def ask_return_date(user_id, context):
    recipient = messages.Recipient(user_id)
    one_way_button = elements.PostbackButton(
        title="One way only",
        payload="oneWayTicket"
    )
    template = templates.ButtonTemplate(
        text="What date and time would you like to return? Please type if not one way.",
        buttons=[
            one_way_button
        ]
    )
    attachment = attachments.TemplateAttachment(template=template)
    message = messages.Message(attachment=attachment)
    request = messages.MessageRequest(recipient, message)
    messenger.send(request)
    return context


def ask_to_save_ticket_preferences(user_id, context):
    recipient = messages.Recipient(user_id)
    yes_button = elements.PostbackButton(
        title="Yes",
        payload="saveTicketPreferences"
    )
    no_button = elements.PostbackButton(
        title="No",
        payload="doNotSaveTicketPreferences"
    )
    template = templates.ButtonTemplate(
        text="Would you like to save your ticket preferences?",
        buttons=[
            yes_button, no_button
        ]
    )
    attachment = attachments.TemplateAttachment(template=template)
    message = messages.Message(attachment=attachment)
    request = messages.MessageRequest(recipient, message)
    messenger.send(request)
    return context


def ask_ticket_speed_references(user_id, context):
    global user_conversations
    user_dictionary = next(item for item in user_conversations if item["recipient"]['id'] == user_id)
    recipient = messages.Recipient(user_id)
    if 'returnTime' in context:
        if user_dictionary['ticketPreference'] == "":
            cheaper_button = elements.PostbackButton(
                title="Cheaper",
                payload="ticketPreferenceCheaper"
            )
            sweet_spot_button = elements.PostbackButton(
                title="Sweet Spot",
                payload="ticketPreferenceSweetSpot"
            )
            faster_button = elements.PostbackButton(
                title="Faster",
                payload="ticketPreferenceFaster"
            )
            template = templates.ButtonTemplate(
                text="What are your ticket preferences?",
                buttons=[
                    cheaper_button, sweet_spot_button, faster_button
                ]
            )
        else:
            use_old_preference_button = elements.PostbackButton(
                title="Use " + user_dictionary['ticketPreference'],
                payload="useOldTicketPreference"
            )
            dont_use_old_preference_button = elements.PostbackButton(
                title="Change ticket prefs",
                payload="changePreferences"
            )
            template = templates.ButtonTemplate(
                text="You have a saved preference. Would you like to use that?",
                buttons=[
                    use_old_preference_button, dont_use_old_preference_button
                ]
            )
        attachment = attachments.TemplateAttachment(template=template)
        message = messages.Message(attachment=attachment)
        request = messages.MessageRequest(recipient, message)
        messenger.send(request)
    return context


def start_over(user_id, context):
    global user_conversations
    user_dictionary = next(item for item in user_conversations if item["recipient"]['id'] == user_id)
    user_dictionary['context'] = {}
    user_dictionary['payment'] = { "name": "",
                             "cardNumber": "",
                             "phoneNumber": "",
                             "email": "",
                             "address":"",
                             "railcard": ""}
    recipient = messages.Recipient(user_id)
    buy_tickets_button = elements.PostbackButton(
        title="Buy Tickets",
        payload="buyTickets"
    )
    help_button = elements.PostbackButton(
        title="Display Help",
        payload="displayHelp"
    )
    template = templates.ButtonTemplate(
        text="Is there anything else I can help you with?",
        buttons=[
            buy_tickets_button, help_button
        ]
    )
    attachment = attachments.TemplateAttachment(template=template)
    message = messages.Message(attachment=attachment)
    request = messages.MessageRequest(recipient, message)
    messenger.send(request)


actions = {
}


def reset_chat(dictionary_entry):
    dictionary_entry["context"] = {}


def send_text_message(user_id, message):
    data = {
        "recipient": {"id": user_id},
        "message": {"text": message}
    }
    requests.post("https://graph.facebook.com/v2.6/me/messages?access_token=" + FB_ACCESS_TOKEN, json=data)


def send_image_message(user_id, image):
    data = {
        "recipient": {"id": user_id},
        "message": {"attachment": {"type":"image",
                                   "payload":{
                                       "url":image
                                   }

        }}
    }
    request = requests.post("https://graph.facebook.com/v2.6/me/messages?access_token=" + FB_ACCESS_TOKEN, json=data)
    print(request.content)


def change_dates(user_id, context):
    context['departureTime'] = ""
    context['returnTime'] = ""
    context.pop('oneWay', None)
    send_text_message(user_id, "What date and time would you like to depart? Please use format: 5th July 5pm")


def ask_to_save_payment(user_id, context):
    recipient = messages.Recipient(user_id)
    yes_button = elements.PostbackButton(
        title="Yes",
        payload="yesPayment"
    )
    no_button = elements.PostbackButton(
        title="No",
        payload="noPayment"
    )
    template = templates.ButtonTemplate(
        text="Awesome. Would you like to save these details for next time?",
        buttons=[
            yes_button, no_button
        ]
    )
    attachment = attachments.TemplateAttachment(template=template)
    message = messages.Message(attachment=attachment)
    request = messages.MessageRequest(recipient, message)
    messenger.send(request)
    pass


def set_railcard(user_id, context, railcardType):
    global user_conversations
    user_dictionary = next(item for item in user_conversations if item["recipient"]['id'] == user_id)
    payment = user_dictionary['payment']
    payment['railcard'] = railcardType
    ask_to_save_payment(user_id, context)


def save_payment(user_id, context, param):
    global user_conversations
    user_dictionary = next(item for item in user_conversations if item["recipient"]['id'] == user_id)
    if param == "yes":
        user_dictionary['savedPayment'] = user_dictionary['payment']
    send_text_message(user_id, "BOOM!")
    send_image_message(user_id,
                     'http://media1.popsugar-assets.com/files/thumbor/cF-Sy4P43JgfhWb46ANv32uYG0c/fit-in/1024x1024/filters:format_auto.!!.:strip_icc.!!./2014/09/25/940/n/1922283/2be4b918df41a20a_thumb_temp_cover_file8453151411671428/i/Best-Fresh-Prince-Bel-Air-Dancing-GIFs.gif')
    send_text_message(user_id, "<Ticket displayed here and emailed to user>")
    user_dictionary['savedInformation'] = "yes"
    start_over(user_id, context)


def ask_to_use_saved_payment(user_id, context):
    global user_conversations
    user_dictionary = next(item for item in user_conversations if item["recipient"]['id'] == user_id)
    recipient = messages.Recipient(user_id)
    use_saved_payment_button = elements.PostbackButton(
        title=user_dictionary['savedPayment']['email'],
        payload="useSavedPayment"
    )
    dont_use_saved_payment_button = elements.PostbackButton(
        title="New email address",
        payload="enterNewPayment"
    )
    template = templates.ButtonTemplate(
        text="You have a saved email address. Would you like to use that?",
        buttons=[
            use_saved_payment_button, dont_use_saved_payment_button
        ]
    )
    attachment = attachments.TemplateAttachment(template=template)
    message = messages.Message(attachment=attachment)
    request = messages.MessageRequest(recipient, message)
    messenger.send(request)
    return context


def handlePostback(user_id, postback, context):
    global user_conversations
    user_dictionary = next(item for item in user_conversations if item["recipient"]['id'] == user_id)
    context = user_dictionary['context']
    if postback == "yesConfirmation":
        wit_client.run_actions(user_id, "Yes", context=context)
    elif postback == "noConfirmation":
        wit_client.run_actions(user_id, "No", context=context)
    elif postback == "singleTicket":
        wit_client.run_actions(user_id, "Single", context=context)
    elif postback == "returnTicket":
        wit_client.run_actions(user_id, "Return", context=context)
    elif postback == "displayHelp":
        send_text_message(user_id, "This has not been implemented yet :O")
        #To do
        pass
    elif postback == "buyTickets":
        send_text_message(user_id, "Thanks, " + user_dictionary['firstName'] + ". Let's get a ticket!")
        send_text_message(user_id, ":D")
        if user_dictionary['savedHome'] != "" or user_dictionary['savedUniversity'] != "":
            askUserForDestination(user_id, user_dictionary['savedHome'], user_dictionary['savedUniversity'])
        else:
            send_text_message(user_id, "Where are you travelling to today?")
    elif postback == "saveLocationAsHome":
        memorize_location(user_id, context, "home")
    elif postback == "saveLocationAsUniversity":
        memorize_location(user_id, context, "university")
    elif postback == "saveLocationAsOther":
        memorize_location(user_id, context, "other")
    elif postback == "askReturnDate":
        ask_return_date(user_id, context)
    elif postback == "ticketPreferenceCheaper":
        set_ticket_preferences(user_id, context, "Cheaper")
    elif postback == "ticketPreferenceSweetSpot":
        set_ticket_preferences(user_id, context, "Sweet Spot")
    elif postback == "ticketPreferenceFaster":
        set_ticket_preferences(user_id, context, "Faster")
    elif postback == "saveTicketPreferences":
        save_ticket_preferences(user_id, context, "yes")
    elif postback == "doNotSaveTicketPreferences":
        save_ticket_preferences(user_id, context, "no")
    elif postback == "saveLocationConfirmedYes":
        memorize_location(user_id, context, "yes")
    elif postback == "saveLocationConfirmedNo":
        memorize_location(user_id, context, "no")
    elif postback == "ticketSelected":
        send_text_message(user_id, "Great choice!")
        if user_dictionary['savedPayment']:
            ask_to_use_saved_payment(user_id, context)
        else:
            send_text_message(user_id, "I just need some details from you.")
            send_text_message(user_id, "What's your email address?")
    elif postback == "changePreferences":
        user_dictionary['ticketPreference'] = ""
        ask_ticket_speed_references(user_id, context)
    elif postback == "changeDates":
        change_dates(user_id, context)
    elif postback == "yesRailcard":
        set_railcard(user_id, context, "Young Persons")
    elif postback == "otherRailcard":
        send_text_message(user_id, "What's this other railcard you speak of?")
    elif postback == "noRailcard":
        set_railcard(user_id, context, "no")
    elif postback == "yesPayment":
        save_payment(user_id, context, "yes")
    elif postback == "noPayment":
        save_payment(user_id, context, "no")
    elif postback == "oneWayTicket":
        context['oneWay'] = "yes"
        context['returnTime'] = ""
        ask_ticket_speed_references(user_id, context)
    elif postback == "useOldTicketPreference":
        context['ticketPreference'] = user_dictionary['ticketPreference']
        save_ticket_preferences(user_id, context, "no")
    elif postback == "useSavedPayment":
        context['payment'] = user_dictionary['savedPayment']
        if 'railcard' in user_dictionary['savedPayment']:
            ask_to_save_used_railcard(user_id, context)
        else:
            ask_for_railcard(user_id, context)
    elif postback == "enterNewPayment":
        send_text_message(user_id, "What's your email address?")
    elif postback == "useSavedHome":
        if 'location:destination' not in context:
            context['location:destination'] = user_dictionary['savedHome']
            ask_user_for_origin(user_id, user_dictionary['savedHome'], user_dictionary['savedUniversity'])
        else:
            context['location:origin'] = user_dictionary['savedHome']
            send_text_message(user_id, "What date and time would you like to depart? Please use format: 5th July 5pm")
    elif postback == "useSavedUniversity":
        if 'location:destination' not in context:
            context['location:destination'] = user_dictionary['savedUniversity']
            ask_user_for_origin(user_id, user_dictionary['savedHome'], user_dictionary['savedUniversity'])
        else:
            context['location:origin'] = user_dictionary['savedUniversity']
            send_text_message(user_id, "What date and time would you like to depart? Please use format: 5th July 5pm")
    elif postback == "useOtherLocation":
        send_text_message(user_id, "What's the name of this... other location?")
    elif postback == "yesSavedRailcard":
        save_payment(user_id, context, "no")
    elif postback == "noSavedRailcard":
        ask_for_railcard(user_id, context)
    # else:
    #     #Put this in the correct place.
    #     startOver(user_id, context)


def send_single_or_return_template(user_id):
    recipient = messages.Recipient(user_id)
    single_button = elements.PostbackButton(
        title="Single",
        payload="singleTicket"
    )
    return_button = elements.PostbackButton(
        title="Return",
        payload = "returnTicket"
    )
    template = templates.ButtonTemplate(
        text="Would you like a Single or a Return ticket?",
        buttons=[
            single_button, return_button
        ]
    )
    attachment = attachments.TemplateAttachment(template=template)
    message = messages.Message(attachment=attachment)
    request = messages.MessageRequest(recipient, message)
    messenger.send(request)


def send_yes_no_template(user_id):
    recipient = messages.Recipient(user_id)
    yes_button = elements.PostbackButton(
        title="Yes",
        payload = "yesConfirmation"
    )
    no_button = elements.PostbackButton(
        title="No",
        payload = "noConfirmation"
    )
    template = templates.ButtonTemplate(
        text="Is this correct?",
        buttons=[
            yes_button, no_button
        ]
    )
    attachment = attachments.TemplateAttachment(template=template)
    message = messages.Message(attachment=attachment)
    request = messages.MessageRequest(recipient, message)
    messenger.send(request)


def ask_user_for_origin(user_id, savedHome, savedUniversity):
    recipient = messages.Recipient(user_id)
    if savedHome:
        home_location_button = elements.PostbackButton(
            title=savedHome,
            payload="useSavedHome"
        )
    if savedUniversity:
        university_location_button = elements.PostbackButton(
            title=savedUniversity,
            payload="useSavedUniversity"
        )
    other_location_button = elements.PostbackButton(
            title="Other",
            payload="useOtherLocation"
        )
    if savedHome and savedUniversity:
        template = templates.ButtonTemplate(
            text="What about for your origin?",
            buttons=[
                home_location_button, university_location_button, other_location_button
            ]
        )
    elif savedHome:
        template = templates.ButtonTemplate(
            text="What about for your origin?",
            buttons=[
                home_location_button, other_location_button
            ]
        )
    elif savedUniversity:
        template = templates.ButtonTemplate(
            text="What about for your origin?",
            buttons=[
                university_location_button, other_location_button
            ]
        )
    attachment = attachments.TemplateAttachment(template=template)
    message = messages.Message(attachment=attachment)
    request = messages.MessageRequest(recipient, message)
    messenger.send(request)
    return


def askUserForDestination(user_id, savedHome, savedUniversity):
    recipient = messages.Recipient(user_id)
    if savedHome:
        home_location_button = elements.PostbackButton(
            title=savedHome,
            payload="useSavedHome"
        )
    if savedUniversity:
        university_location_button = elements.PostbackButton(
            title=savedUniversity,
            payload="useSavedUniversity"
        )
    other_location_button = elements.PostbackButton(
            title="Other",
            payload="useOtherLocation"
        )
    if savedHome and savedUniversity:
        template = templates.ButtonTemplate(
            text="Would you like to use a previous location as your destination?",
            buttons=[
                home_location_button, university_location_button, other_location_button
            ]
        )
    elif savedHome:
        template = templates.ButtonTemplate(
            text="Would you like to use a previous location as your destination?",
            buttons=[
                home_location_button, other_location_button
            ]
        )
    elif savedUniversity:
        template = templates.ButtonTemplate(
            text="Would you like to use a previous location as your destination?",
            buttons=[
                university_location_button, other_location_button
            ]
        )
    attachment = attachments.TemplateAttachment(template=template)
    message = messages.Message(attachment=attachment)
    request = messages.MessageRequest(recipient, message)
    messenger.send(request)
    return


def ask_for_railcard(user_id, context):
    recipient = messages.Recipient(user_id)
    young_persons_button = elements.PostbackButton(
        title="16-25 Railcard",
        payload="yesRailcard"
    )
    other_button = elements.PostbackButton(
        title="Other",
        payload="otherRailcard"
    )
    no_button = elements.PostbackButton(
        title="No",
        payload="noRailcard"
    )
    template = templates.ButtonTemplate(
        text="One more thing: do you have a railcard?",
        buttons=[
            young_persons_button, other_button, no_button
        ]
    )
    attachment = attachments.TemplateAttachment(template=template)
    message = messages.Message(attachment=attachment)
    request = messages.MessageRequest(recipient, message)
    messenger.send(request)


def ask_to_save_used_railcard(user_id, context):
    global user_conversations
    user_dictionary = next(item for item in user_conversations if item["recipient"]['id'] == user_id)
    recipient = messages.Recipient(user_id)
    yes_railcard_button = elements.PostbackButton(
        title="Yes",
        payload="yesSavedRailcard"
    )
    no_railcard_button = elements.PostbackButton(
        title="No",
        payload="noRailcard"
    )
    template = templates.ButtonTemplate(
        text="You have a saved railcard: " + user_dictionary['savedPayment']['railcard'] + ". Would you like to use it?",
        buttons=[
            yes_railcard_button, no_railcard_button
        ]
    )
    attachment = attachments.TemplateAttachment(template=template)
    message = messages.Message(attachment=attachment)
    request = messages.MessageRequest(recipient, message)
    messenger.send(request)


@app.route('/incoming', methods=['POST'])
def incomingPost():
    global user_conversations
    data = request.json
    try:
        deliveryRequest = data['entry'][0]['messaging'][0]['delivery']
        print("Ignoring")
        # Ignore delivery requests from Facebook (this can be modified in Page settings
        return 'ok'
    except Exception:
        pass
    print("Incoming request: " + str(data))
    user_id = data['entry'][0]['messaging'][0]['sender']['id']

    # Adds user ID to the dictionary/database if it does not exist already. This is so we can keep track of their
    # conversations. In production this would be stored in an PostgreSQL database using Django.
    if next((item for item in user_conversations if item["recipient"]['id'] == user_id), False) == False:
        user_conversations.append(
            {
                "recipient": {"id": user_id},
                "context":{},
                "savedHome":"",
                "savedUniversity":"",
                "ticketPreference": "",
                "payment": { "email": "",
                             "railcard": ""}
                ,
                "savedPayment": {}

            }
        )

    # Then selects that recently added dictionary entry
    user_dictionary = next(item for item in user_conversations if item["recipient"]['id'] == user_id)
    print("correct dictionary entry: " + str(user_dictionary))

    if 'firstName' not in user_dictionary:
        response = requests.get('https://graph.facebook.com/v2.6/' + user_id + '?fields=first_name,last_name,profile_pic,locale,timezone,gender&access_token=' + FB_ACCESS_TOKEN)
        response = response.json()
        user_dictionary['firstName'] = response['first_name']

    if 'postback' in data['entry'][0]['messaging'][0]:
        # Check if the request is a postback
        print("postback")
        postback = data['entry'][0]['messaging'][0]['postback']['payload']
        handlePostback(user_id, postback, user_dictionary['context'])

    else:
        # Check if the request is a text message and get the text
        message = data['entry'][0]['messaging'][0]['message']['text']
        context = user_dictionary['context']

        if "restart" in message.lower():
            start_over(user_id, context)
            return 'ok'
        payment = user_dictionary['payment']

        print("Context: " + str(context))
        if 'location:destination' not in context:
            response = wit_client.message(message)
            location = first_entity_value(response['entities'], 'location')
            if location:
                context['location:destination'] = location.title()
                ask_location_nature(user_id, context)
            else:
                send_text_message(user_id, "That station was not recognised. Please try again.")
                return 'ok'
        elif 'location:origin' not in context:
            response = wit_client.message(message)
            location = first_entity_value(response['entities'], 'location')
            if location:
                context['location:origin'] = location.title()
                ask_location_nature(user_id, context)
            else:
                send_text_message(user_id, "That station was not recognised. Please try again.")
                return 'ok'
        elif 'departureTime' not in context:
            response = wit_client.message(message)
            datetime = first_entity_value(response['entities'], 'datetime')
            if datetime:
                context['departureTime'] = datetime
                ask_return_date(user_id, context)
            else:
                send_text_message(user_id, "That date and time was not recognised. Please try again.")
                return 'ok'
        elif 'returnTime' not in context and 'oneWay' not in user_dictionary:
            response = wit_client.message(message)
            datetime = first_entity_value(response['entities'], 'datetime')
            if datetime:
                context['returnTime'] = datetime
                ask_ticket_speed_references(user_id, context)
            else:
                send_text_message(user_id, "That date and time was not recognised. Please try again.")
                return 'ok'
        # This is if the user wants to change their travel time.
        # This context check is used so an exception is not thrown. It will only get caught by this if
        # the context for departureTime and returnTime had previously been set and then set to "".
        elif context['departureTime'] == "":
            response = wit_client.message(message)
            datetime = first_entity_value(response['entities'], 'datetime')
            if datetime:
                context['departureTime'] = datetime
                ask_return_date(user_id, context)
            else:
                send_text_message(user_id, "That date and time was not recognised. Please try again.")
                return 'ok'
        elif context['returnTime'] == "" and 'oneWay' not in context:
            response = wit_client.message(message)
            datetime = first_entity_value(response['entities'], 'datetime')
            if datetime:
                context['returnTime'] = datetime
                if 'ticketPreference' not in context:
                    ask_ticket_speed_references(user_id, context)
                else:
                    display_sample_ticket(user_id, context)
            else:
                send_text_message(user_id, "That date and time was not recognised. Please try again.")
                return 'ok'
        elif payment['email'] == "":
            payment['email'] = message
            if 'railcard' in user_dictionary['savedPayment']:
                ask_to_save_used_railcard(user_id, context)
            else:
                ask_for_railcard(user_id, context)
        elif payment['railcard'] == "":
            payment['railcard'] = message
            set_railcard(user_id, context, "no")

    return 'ok'

wit_client = Wit(WIT_SERVER_TOKEN, actions)


if __name__ == "__main__":
    app.run(port=8080, debug=True)