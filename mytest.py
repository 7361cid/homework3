import requests

response = requests.post('http://127.0.0.1:8080/method/',
                         json={"account": "horns&hoofs", "login": "h&f", "method":
                             "online_score",
                               "token": "55cc9ce545bcd144300fe9efc28e65d415b923ebb6be1e19d2750a2c03e80dd209a27954dca045e5bb12418e7d89b6d718a9e35af34e14e1d5bcd5a08f21fc95",
                               "arguments": {"phone": "79175002040", "email": "stupnikov@otus.ru",
                                             "first_name": "Стансилав", "last_name":
                                                 "Ступников", "birthday": "01.01.1990",
                                             "gender": 1}})

response2 = requests.post('http://127.0.0.1:8080/method/',
                          json={"account": "horns&hoofs", "login": "h&f", "method":
                              "clients_interests",
                                "token": "55cc9ce545bcd144300fe9efc28e65d415b923ebb6be1e19d2750a2c03e80dd209a27954dca045e5bb12418e7d89b6d718a9e35af34e14e1d5bcd5a08f21fc95",
                                "arguments": {"client_ids": [1, 2, 3], "date": "01.01.1990"}})

print(response)
print(response2)
