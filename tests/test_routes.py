"""
Account API Service Test Suite

Test cases can be run with the following:
  nosetests -v --with-spec --spec-color
  coverage report -m
"""
import os
import logging
from unittest import TestCase
from tests.factories import AccountFactory
from service.common import status  # HTTP Status Codes
from service.models import db, Account, init_db
from service.routes import app

DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)

BASE_URL = "/accounts"


######################################################################
#  T E S T   C A S E S
######################################################################
class TestAccountService(TestCase):
    """Account Service Tests"""

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        init_db(app)

    @classmethod
    def tearDownClass(cls):
        """Runs once before test suite"""

    def setUp(self):
        """Runs before each test"""
        db.session.query(Account).delete()  # clean up the last tests
        db.session.commit()

        self.client = app.test_client()

    def tearDown(self):
        """Runs once after each test case"""
        db.session.remove()

    ######################################################################
    #  H E L P E R   M E T H O D S
    ######################################################################

    def _create_accounts(self, count):
        """Factory method to create accounts in bulk"""
        accounts = []
        for _ in range(count):
            account = AccountFactory()
            response = self.client.post(BASE_URL, json=account.serialize())
            self.assertEqual(
                response.status_code,
                status.HTTP_201_CREATED,
                "Could not create test Account",
            )
            new_account = response.get_json()
            account.id = new_account["id"]
            accounts.append(account)
        return accounts

    ######################################################################
    #  A C C O U N T   T E S T   C A S E S
    ######################################################################

    def test_index(self):
        """It should get 200_OK from the Home Page"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_health(self):
        """It should be healthy"""
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "OK")

    def test_create_account(self):
        """It should Create a new Account"""
        account = AccountFactory()
        response = self.client.post(
            BASE_URL,
            json=account.serialize(),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Make sure location header is set
        location = response.headers.get("Location", None)
        self.assertIsNotNone(location)

        # Check the data is correct
        new_account = response.get_json()
        self.assertEqual(new_account["name"], account.name)
        self.assertEqual(new_account["email"], account.email)
        self.assertEqual(new_account["address"], account.address)
        self.assertEqual(new_account["phone_number"], account.phone_number)
        self.assertEqual(new_account["date_joined"], str(account.date_joined))

    def test_bad_request(self):
        """It should not Create an Account when sending the wrong data"""
        response = self.client.post(BASE_URL, json={"name": "not enough data"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unsupported_media_type(self):
        """It should not Create an Account when sending the wrong media type"""
        account = AccountFactory()
        response = self.client.post(
            BASE_URL,
            json=account.serialize(),
            content_type="test/html"
        )
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    # ADD YOUR TEST CASES HERE ...

    def test_get_account_list(self):
        """It should Get a list of Accounts"""
        self._create_accounts(5)
        # send a self.client.get() request to the BASE_URL
        response = self.client.get(BASE_URL)
        # assert that the resp.status_code is status.HTTP_200_OK
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # get the data from resp.get_json()
        account_data = response.get_json()
        # assert that the len() of the data is 5 (the number of accounts you created)
        self.assertEqual(len(account_data), 5)

    def test_get_account(self):
        """It should Read a single Account"""
        account = self._create_accounts(1)[0]
        # make a call to self.client.post() to create the account
        response = self.client.get(f"{BASE_URL}/{account.id}", content_type="application/json")
        # assert that the resp.status_code is status.HTTP_200_OK
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # get the data from resp.get_json()
        data = response.get_json()
        # assert that data["name"] equals the account.name
        self.assertEqual(data["name"], account.name)

    def test_get_account_with_wrong_id(self):
        """It should Raise a 404 error and return an empty dict if account_id does not exist in DB"""
        accounts = self._create_accounts(5)
        max_id = max([i.id for i in accounts])
        account_id = max_id + 999
        print(f"\n\n===1(1)====== max_id: {max_id}, account_id: {account_id}\n\n")

        # make a call to self.client.post() to create the account
        response = self.client.get(f"{BASE_URL}/{account_id}", content_type="application/json")
        # assert that the resp.status_code is status.HTTP_200_OK
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn(f"Account with id [{account_id}] could not be found.".encode("utf-8"), response.data)

    def test_delete_account(self):
        """It should Delete an Account with the given account_id"""
        account = self._create_accounts(1)[0]
        account_id = account.id

        # send a self.client.delete() request to the BASE_URL with an id of an account
        response = self.client.delete(f"{BASE_URL}/{account_id}")

        # assert that the resp.status_code is status.HTTP_204_NO_CONTENT
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # test finding the deleted account in DB with the given ID, expect 404 and null return
        delete_again_response = self.client.delete(f"{BASE_URL}/{account_id}")
        self.assertEqual(delete_again_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn(f"Account with id [{account_id}] could not be found.".encode("utf-8"), delete_again_response.data)

    def test_update_account(self):
        """It should Update an existing Account with the given account_id"""
        # create an Account to update
        test_account = self._create_accounts(1)[0]
        account_id = test_account.id

        print(f"\n\n===2(1)====== test_account: {test_account}\n\n")

        # get the data from resp.get_json() as new_account
        new_account = test_account.serialize()
        # change new_account["name"] to something known
        new_name = f"{test_account.name}_xxx"
        new_account['name'] = new_name

        print(f"\n\n===2(2)====== new_account: {new_account}\n\n")
        print(f"\n\n===2(3)====== new_name: {new_name}\n\n")
        # Update the Account by account_id with new data
        put_response = self.client.put(f"{BASE_URL}/{account_id}", json=new_account)
        self.assertEqual(put_response.status_code, status.HTTP_200_OK)

        # get the data from resp.get_json() as updated_account
        updated_account = put_response.get_json()
        print(f"\n\n===2(4)====== updated_account: {updated_account}\n\n")
        self.assertEqual(updated_account['name'], new_name)

    def test_update_account_with_bad_id(self):
        """It should Update an existing Account with the given account_id"""
        # create an Account to update
        test_account = self._create_accounts(1)[0]
        account_id = test_account.id + 999

        # get the data from resp.get_json() as new_account
        same_data = test_account.serialize()

        # Update the Account by account_id with new data
        put_response = self.client.put(f"{BASE_URL}/{account_id}", json=same_data)
        self.assertEqual(put_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn(f"Account with id [{account_id}] could not be found.".encode("utf-8"), put_response.data)


        
