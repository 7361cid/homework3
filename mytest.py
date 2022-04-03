import requests

response = requests.post('http://127.0.0.1:8080/method/',
                         json={"account": "horns&hoofs", "login": "h&f", "method":
                             "online_score",
                               "token": "55cc9ce545bcd144300fe9efc28e65d415b923ebb6be1e19d2750a2c03e80dd209a27954dca045e5bb12418e7d89b6d718a9e35af34e14e1d5bcd5a08f21fc95",
                               "arguments": {}})

response2 = requests.post('http://127.0.0.1:8080/method/',
                          json={"account": "horns&hoofs", "login": "h&f", "method":
                              "clients_interests",
                                "token": "55cc9ce545bcd144300fe9efc28e65d415b923ebb6be1e19d2750a2c03e80dd209a27954dca045e5bb12418e7d89b6d718a9e35af34e14e1d5bcd5a08f21fc95",
                                "arguments": {"client_ids": [1, 2, 3]}, "date":'03.04.2022'})

print(response, response.text)
print(response2, response2.text)
