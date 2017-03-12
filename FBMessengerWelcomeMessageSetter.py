import requests
import json

ACCESS_TOKEN = "{removed}"

data = {
    "setting_type":"call_to_actions",
    "thread_state":"new_thread",
    "call_to_actions":[
        {
        "message":{
            "attachment":{
                "type":"template",
                "payload":{
                    "template_type":"button",
                    "text":"Hi, I'm your assistant! I'll help you find cheaper train tickets. If you need any help just let me know by tapping 'Help'",
                    "buttons":[
                        {
                            "type":"postback",
                            "title":"Buy Tickets",
                            "payload":"buyTickets"
                        },
                        {
                            "type":"postback",
                            "title":"Help",
                            "payload":"displayHelp"
                        }
                    ]
                }
            }
        }
        }
    ]
}

request = requests.post("https://graph.facebook.com/v2.6/196339474098546/thread_settings?access_token=" + ACCESS_TOKEN, json=data)

print(request.content.decode("utf-8"))
