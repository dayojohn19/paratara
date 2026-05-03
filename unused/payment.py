from requests.auth import HTTPBasicAuth
SECRET_KEY = "sk_live_qEeenZi789JGFsBXYMHSbAKe"
auth = HTTPBasicAuth(SECRET_KEY, '')
import requests
import time
class PayMongoGCash:
    def __init__(self, secret_key):
        self.secret_key = secret_key
        self.auth = HTTPBasicAuth(secret_key, '')
        self.base_url = "https://api.paymongo.com/v1"
        self.hashedapi = "c2tfbGl2ZV9xRWVlblppNzg5SkdGc0JYWU1IU2JBS2U6"
        self.amount = 0
        self.payment_id = ''
        self.payment_intent_key = ''
    def create_payment_intent(self, amount_php):
        self.amount = amount_php
        """Create a payment intent. Amount in PHP"""
        url = f"{self.base_url}/payment_intents"
        payload = {
            "data": {
                "type": "payment_intent",
                "attributes": {
                    "amount": int(amount_php * 100),  # convert PHP to centavos
                    "payment_method_allowed": ["qrph", "card", "dob", "paymaya", "billease", "gcash", "grab_pay"],
                    "payment_method_options": { "card": { "request_three_d_secure": "any" } },
                    "currency": "PHP",
                    "capture_type": "automatic"
                }
            }
        }
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": f"Basic {self.hashedapi}"
        }        
        response = requests.post(url, headers=headers, json=payload)
        data = response.json()
        self.payment_id = data['data']['id']
        self.payment_intent_key = data['data']['attributes']['client_key']
        return data
        print(data)
        time.sleep(2)
        return self.retreive_payment_intent(payment_intent_id, payment_intent_key)
        # return response.json()

    def retreive_payment_intent(self, payment_intent_id, payment_intent_key):
        url = f"{self.base_url}/payment_intents"

        url = f"https://api.paymongo.com/v1/payment_intents/{payment_intent_id}"

        headers = {
            "accept": "application/json",
            "authorization": f"Basic {self.hashedapi}"
        }

        response = requests.get(url, headers=headers)
        print('retreive payment intent')
        print(response.text)        
        
        return self.attach_payment_intent(payment_intent_id, payment_intent_key)


    def attach_payment_intent(self, payment_intent_id, payment_intent_key):
        import requests
        url = f"{self.base_url}/payment_intents/{payment_intent_id}/attach"
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": f"Basic {self.hashedapi}"
        }
        payload = {
            "data": {
                "attributes": {
                    "payment_method": payment_intent_id,
                    "client_key": payment_intent_key
                }
            }
        }
        # response = requests.post(url, headers=headers)
        response = requests.post(url, headers=headers, json=payload)
        print(response.text)        
        print('\n\n --- END')
        return


    


    def create_payment_method(self, email, name, phone):
        """Create GCash payment method"""
        # url = "https://api.paymongo.com/v1/payment_methods"
        url = f"{self.base_url}/payment_methods"
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "authorization": f"Basic {self.hashedapi}"
        }        
        # data = {
        #     "data": {
        #         "id": self.payment_id,
        #         "type": "payment_method",
        #         "attributes": {
        #         "detail": {
        #             "last4": "4242",
        #             "exp_month": 1,
        #             "exp_year": 24
        #         },                    
        #             "amount": int(self.amount * 100),  # convert PHP to centavos
        #             "currency": "PHP",
        #             "description": "Test GCash payment",
        #             "statement_descriptor": "The Barkery Shop",
        #             "status": "awaiting_payment_method",
        #             "livemode": True,
        #             "client_key": self.payment_intent_key,
        #             "created_at": 1586179682,
        #             "updated_at": 1586179682,
        #             "last_payment_error": None,
        #             "payment_method_allowed": [
        #                 "card", "gcash"
        #             ],
        #             "payments": [],
        #             "next_action": None,
        #             "payment_method_options": {
        #                 "card": {
        #                     "request_three_d_secure": "any"
        #                 }
        #             },
        #             "metadata": {
        #                 "yet_another_metadata": "good metadata",
        #                 "reference_number": "X1999"
        #             },                    


        #             # "capture_type": "automatic",
        #             # "payment_method_allowed": ["gcash"],  # <-- must include gcash

        #             # "billing": {
        #             #     "email": email,
        #             #     "name": name,
        #             #     "phone": phone
        #             # }
        #         }
        #     }
        # }
       
       
        data = {
            "data": {
                "attributes": {
                    "type" : "gcash",
                    "billing": {
                        "name": "John Doe",
                        "email": "john.doe@example.com",
                        "phone": "09123456789",
                    },                    
                    "amount": 10000,  # ₱100.00 in centavos
                    "payment_method_allowed": ["gcash", "card"],
                    "currency": "PHP",
                    "capture_type": "automatic",
                    "statement_descriptor": "The Barkery Shop",
                    "description": "Test GCash payment",
                    "return_url": "https://your-online-store.com/success",
                    "metadata": {
                        "reference_number": "X1999"
                    }
                }
            }
        }        

     
        response = requests.post(url, auth=self.auth, json=data)
        data = response.json()
        return data        
        payment_intent_id = response['data']['id']

        

        return response.json()




    def attach_payment_method(self, payment_intent_id, payment_method_id, client_key):
        """Attach payment method to the payment intent"""
        url = f"{self.base_url}/payment_intents/{payment_intent_id}/attach"
        data = {
            "data": {
                "attributes": {
                    "payment_method": payment_method_id,
                    "client_key": client_key
                }
            }
        }
        response = requests.post(url, auth=self.auth, json=data)
        print('Attach_payment Method: ',response.json())
        return response.json()

    def get_gcash_payment_link(self, attach_response):
        """Extract GCash checkout URL from attach response"""
        try:
            return attach_response['data']['attributes']['next_action']['redirect']['url']
        except KeyError:
            return None

    def check_payment_status(self, payment_intent_id):
        """Check the status of a payment intent"""
        url = f"{self.base_url}/payment_intents/{payment_intent_id}"
        response = requests.get(url, auth=self.auth)
        return response.json()


# --- Example Usage ---
if __name__ == "__main__":
    SECRET_KEY = "sk_live_qEeenZi789JGFsBXYMHSbAKe"  # replace with your secret key

    paymongo = PayMongoGCash(SECRET_KEY)

    # 1. Create payment intent
    intent = paymongo.create_payment_intent(100)  # PHP 100
    print(f' \n Intent Created : {intent} \n \n')
    payment_intent_id = intent['data']['id']
    print('payment ID: ',payment_intent_id)
    client_key = intent['data']['attributes']['client_key']
    print("""

    Intent Created


""")
    # 2. Create payment method
    method = paymongo.create_payment_method(
        email="dayo_john16@yahoo.com",
        name="john christoper dayo",
        phone="+639568543802"
    )
    print(f' Checking Method {method}') 
    payment_method_id = method['data']['id']
    print("""

    Method Created


""")
    # 3. Attach payment method
    attach = paymongo.attach_payment_method(payment_intent_id, payment_method_id, client_key)

    # 4. Get GCash checkout link
    gcash_url = paymongo.get_gcash_payment_link(attach)
    print("Send this GCash payment link to customer:", gcash_url)

    # 5. Optional: Poll for payment status
    time.sleep(5)
    status = paymongo.check_payment_status(payment_intent_id)
    print("Payment status:", status['data']['attributes']['status'])

