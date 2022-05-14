

from PyQt5 import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from collections import namedtuple
import typing
import sqlite3
import datetime
import os
import json

class BossLogin:
  username = "test"
  password = "test"

User = namedtuple("User", ["id", "name", "date", "payment", 'tags'])
Item = namedtuple("Item", ["user", "widgets", 'row'])



def jaro(a: str, b: str):
    if a == b:
      return 1.0
    len1 = len(a); len2 = len(b)
    if 0 in [len1, len2]:
      return 0.0

    max_dist = (max(len(a), len(b)) // 2 ) - 1
    match = 0

    hash_a = [0] * len(a); hash_b = [0] * len(b)

    for i in range(len1) :
      for j in range( max(0, i - max_dist), min(len2, i + max_dist + 1)):
        if a[i] == b[j] and hash_b[j] == 0 :
          hash_a[i] = 1; hash_b[j] = 1
          match += 1
          break
    if match == 0:
      return 0.0
    t = 0
    point = 0
    for i in range(len1):
      if hash_a[i]:
        while hash_b[point] == 0:
          point += 1
          if a[i] != b[point]:
            t += 1
          point += 1

    t /= 2

    return ((match / len1 + match / len2 + (match - t) / match ) / 3.0)

def jaro_wink(s1, s2) :
    jaro_dist = jaro(s1, s2)
    if jaro_dist > 0.7:
      prefix = 0
      for i in range(min(len(s1), len(s2))):
        if s1[i] == s2[i]:
          prefix += 1
        else:
          break

      prefix = min(4, prefix)
      jaro_dist += 0.1 * prefix * (1 - jaro_dist)

    return jaro_dist


class Database:
  def __init__(self):
    self.save_file = "./save.sqlite"
    self.connection = sqlite3.connect("./save.sqlite")
    self.cursor = self.connection.cursor()

    self.init()
    print("loaded database")



  def init(self):
    self.cursor.execute("""
      CREATE TABLE IF NOT EXISTS clients ( id INTEGER, name TEXT, date TEXT, payment INTEGER, tags TEXT )
    """)
    self.connection.commit()

  def add_user(self, user: User):
    id, name, date, payment, tags = user
    _tags = ''
    if type(tags) == str:
      _tags = tags
    else:
      _tags = json.dumps(tags)
    _user = User(id, name, date, payment, _tags)
    command = f"INSERT INTO clients (id, name, date, payment, tags) VALUES (?, ?, ?, ?, ?)"
    self.cursor.execute(command, _user)
    del command
    self.connection.commit()

  def get_users(self) -> list[User]:
    command = "SELECT * FROM clients"
    self.cursor.execute(command)
    del command
    return [User(*user) for user in self.cursor.fetchall()]


class MenuBar(QMenuBar):
  def __init__(self, db: Database) -> None:
    super().__init__()
    self.db: Database = db

class ClientAddDialogue(QDialog):
  def __init__(self, db: Database):
    super().__init__()

    self.db: Database = db

    self.setWindowTitle("Add Client")

    QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel

    self.buttonBox = QDialogButtonBox(QBtn)
    self.buttonBox.accepted.connect(self.good)
    self.buttonBox.rejected.connect(self.cancel)

    self.layout = QGridLayout()

    self.input_id_label = QLabel()
    self.input_id_label.setText("ID: ")
    self.input_id_input = QLineEdit()

    self.input_name_label = QLabel()
    self.input_name_label.setText("Name: ")
    self.input_name_input = QLineEdit()

    self.input_date_label = QLabel()
    self.input_date_label.setText("Date: ")
    self.input_date_input = QLineEdit()

    self.input_payment_label = QLabel()
    self.input_payment_label.setText("Payment")
    self.input_payment_input = QLineEdit()

    orders = [
      (self.input_id_label, self.input_id_input),
      (self.input_name_label, self.input_name_input),
      (self.input_date_label, self.input_date_input),
      (self.input_payment_label, self.input_payment_input)
    ]

    x = 0
    for _label, _input in orders:
      y = 0
      for i in [_label, _input]:
        self.layout.addWidget(i, x, y)
        y += 1
      x += 1


    self.layout.addWidget(self.buttonBox)

    self.setLayout(self.layout)

  def good(self):
    user = User(
      id=int(self.input_id_input.text()),
      name=str(self.input_name_input.text()),
      date=str(self.input_date_input.text()),
      payment=int(self.input_payment_input.text()),
      tags=[]
    )

    print(user)

    self.db.add_user(user)
    self.accept()

  def cancel(self):
    self.reject()


class Window(QMainWindow):
  def __init__(self):
    super().__init__()

    self.resize(800, 600)
    self.setWindowTitle("Gym")
    self.show()


    self.db = Database()

    self.container = QWidget()
    self.my_layout = QGridLayout()
    self.container.setLayout(self.my_layout)
    self.setCentralWidget(self.container)

    self.menu_bar = MenuBar(self.db)

    self._items: list[Item] = []

    self.clients = QGroupBox()
    self.clients_layout = QGridLayout()
    self.clients.setLayout(self.clients_layout)

    self.client_table = QTableWidget()

    self.search = QGroupBox()
    self.search_layout = QGridLayout()
    self.search.setLayout(self.search_layout)
    self.clients_layout.addWidget(self.search, 0, 0)

    self.search_label = QLabel()
    self.search_label.setText("Search: ")
    self.search_input = QLineEdit()
    x = 0
    for i in [self.search_label, self.search_input]:
      self.search_layout.addWidget(i, 0, x)
      x += 1
    del x

    self.clients_add_btn = QPushButton()
    self.clients_add_btn.setText("Add")
    self.clients_add_btn.clicked.connect(self.addClient)


    self.config_panel = QGroupBox()
    self.config_panel.setTitle("Config")
    self.config_panel_layout = QGridLayout()
    self.config_panel.setLayout(self.config_panel_layout)

    self.client_table.itemSelectionChanged.connect(self.update_config_panel)



    self.clients_layout.addWidget(self.config_panel, 3, 1)
    self.search_layout.addWidget(self.clients_add_btn, 0, 2)
    self.clients_layout.addWidget(self.client_table, 3, 0)

    self.setup = [
      ("MenuBar", self.menu_bar, 0, 0),
      ("ClientTable", self.clients, 1, 0)
    ]

    for name, widget, row, column in self.setup:
      self.my_layout.addWidget(widget, row, column)

    self.update()

  def addClient(self):
    answer = ClientAddDialogue(self.db)

    if answer.exec():
      print("added")
    else:
      print('canceled')

    self.update()

  def update_config_panel(self):
    item = self.client_table.selectedItems()[0]
    row = item.row()

    _item = [i for i in self._items if i.row == row][0]
    if _item is not None:
      for i in reversed(range(self.config_panel_layout.count())):
        self.config_panel_layout.itemAt(i).widget().setParent(None)


  def update_table(self, users: list[User]):
    self.client_table.setRowCount(len(users))
    self.client_table.setColumnCount(len(User._fields))
    self._items.clear()
    for i in range(len(users)):
      user = users[i]
      peices = [QTableWidgetItem(str(getattr(user, key))) for key in User._fields]
      for x in range(len(peices)):
        self.client_table.setItem(i, x, peices[x])

      self._items.append(Item(user, peices, i))

    self.client_table.setHorizontalHeaderLabels(User._fields)

  def update(self):
    users = self.db.get_users()

    self.update_table(users)






app = QApplication([])

window = Window()

exit(app.exec_())
