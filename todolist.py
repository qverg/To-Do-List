from dataclasses import dataclass
from datetime import date, timedelta
from calendar import monthrange
import os.path

DATE_FORMAT = "%a %d %b"    # e.g. Sat 08 Oct
SAVE_FILE_DATE_FORMAT = "%d/%m/%Y"
TO_DO_ITEMS_SAVE_FILE = os.path.dirname(os.path.abspath(__file__)) + "/data/to_do_items"
INVALID_YEAR = 9999

COLUMN_LENGTHS = (3, 49, 25, 25, 12)
PADDING = 3

HELP_STRING = """Commands:
    > 'add' or '+'      Add a to-do list item
    > 'done [ID]'       Mark an item as done (ID is in the leftmost column)
    > 'del [ID]'        Remove an item
      'remove [ID]'
      'rm [ID]'
    > 'undo'            Undo delete or mark as done
    > 'edit [ID]'       Edit an item (just press enter to leave a field as is)
    > 'finish [ID]'     Mark a recurring item as finished, in effect deleting it
    > 'revert [ID]'     Roll a recurring item back to the previous due date (undo mark as done)
    > 'show'            Show all hidden items (since recurring items with far off due dates are hidden)
    > 'help'            Seems like you've found this already :-)
    > 'delall'          Delete all items
    > 'q'               Quit
      'quit'
      'exit'

For dates you can use:
 - Day of the week          'saturday'  'sat'
 - Today                    'today'     'tod'
 - Tomorrow                 'tomorrow'  'tom'
 - One week from today      'next week'
 - Day/month                '12/10'
The program will not complain if you do this wrong so beware. You can always edit using the 'edit' command.

Possible recurrences are:
 - 'daily'
 - 'weekly'
 - 'monthly'    (possibly a little dodgy but should work ok)

"""

class Communication:
    description = "Description: "
    do_date = "Do date:     "
    due_date = "Due date:    "
    recurrence = "Recurrence:  "
    invalid_recurrence_valid = "Invalid recurrence. Valid:"
    item_does_not_exist = "Item does not exist."
    do = "DO  "
    today = "Today!"
    has_passed = "Has passed!"
    due = "DUE "
    overdue = "OVERDUE!"
    recurs = "Recurs"
    ID = "ID"

class TextFormatting:
    @staticmethod
    def center_justify(string: str, length: int):
        if length % 2 == 0:
            return string.rjust(length//2).ljust(length//2)
        
        return string.rjust(length//2+1).ljust(length//2)

    @staticmethod
    def __all_cursors_complete(items: list[str], cursors):
        for cursor, item in zip(cursors, items):
            if cursor < len(item):
                return False
        return True

    @staticmethod
    def columnize(items: list[str], collengths: tuple[int] | int, padding: int, justify="left") -> str:
        if type(collengths) == int:
            collengths = (collengths for i in items)

        match justify:
            case "left":
                justify = str.ljust
            case "right":
                justify = str.rjust
            case "center":
                justify = TextFormatting.center_justify

        cursors = [0 for i in items]
        out = ""
        while not TextFormatting.__all_cursors_complete(items, cursors):
            for item, collength, cursor in zip(items, collengths, cursors):
                out += justify(item[cursor:cursor+collength], collength)
                out += " "*padding
            out += "\n"
            cursors = [cursor + length for cursor, length in zip(cursors, collengths)]

        return out

class Recurrence:
    WEEKLY = 1
    MONTHLY = 2
    DAILY = 3

    from_text = {
        "weekly" : WEEKLY,
        "monthly" : MONTHLY,
        "daily" : DAILY,
        "" : None,
        "None" : None
    }

    to_text = {
        WEEKLY : "weekly",
        MONTHLY : "monthly",
        DAILY : "daily",
        None : "None"
    }

    to_timedelta = {
        WEEKLY : timedelta(weeks=1),
        MONTHLY : timedelta(days=monthrange(date.today().year, date.today().month)[1]),
        DAILY : timedelta(days=1)
    }

class DateHandler:
    weekdays = {
        "mon" : 0,
        "monday" : 0,
        "tue" : 1,
        "tuesday" : 1,
        "wed" : 2,
        "wednesday" : 2,
        "thu" : 3,
        "thursday" : 3,
        "fri" : 4,
        "friday" : 4,
        "sat" : 5,
        "saturday" : 5,
        "sun" : 6,
        "sunday" : 6,
    }

    common_dates = {
        "tod" : date.today(),
        "today" : date.today(),
        "tom" : date.today() + timedelta(days=1),
        "tomorrow" : date.today() + timedelta(days=1),
        "next week" : date.today() + timedelta(weeks=1),
    }

    @staticmethod
    def get_next_week_day(weekday_str : str) -> date:
        for i in range(1, 8):
            weekday_num = (date.today() + timedelta(days=i)).weekday()
            if DateHandler.weekdays[weekday_str] == weekday_num:
                return date.today() + timedelta(days=i)

    @staticmethod
    def get_date_from_string(string_in: str) -> date:
        string_in = string_in.lower()

        # first handle one-word strings
        for key, value in DateHandler.common_dates.items():
            if string_in == key: return value

        if string_in in DateHandler.weekdays.keys():
            return DateHandler.get_next_week_day(string_in)

        # now handling multi-word strings
        split_by_slash = string_in.split("/")
        if len(split_by_slash) == 2:    # e.g. 12/9
            day = int(split_by_slash[0])
            month = int(split_by_slash[1])
            if month < date.today().month:
                year = date.today().year + 1
            elif month > date.today().month:
                year = date.today().year
            else:
                if day < date.today().day:
                    year = date.today().year + 1
                else:
                    year = date.today().year

            return date(year, month, day)
        elif len(split_by_slash) == 3:
            day = int(split_by_slash[0])
            month = int(split_by_slash[1])
            year = int(split_by_slash[2])

            return date(year, month, day)

        return date(INVALID_YEAR, 1, 1)

@dataclass
class ToDoListItem:
    id: str
    description: str = ""
    do_date: date = None
    due_date: date = None
    recurrence: Recurrence = None

    def populate(self, description: str, do_date_str: str, due_date_str: str, recurrence_str):
        self.description = description
        self.do_date = DateHandler.get_date_from_string(do_date_str)
        self.due_date = DateHandler.get_date_from_string(due_date_str)
        self.recurrence = Recurrence.from_text[recurrence_str]

    def edit(self, being_created = False):
        if being_created:
            print(Communication.description, end=" ")
            self.description = input()
            print(Communication.do_date, end=" ")
            self.do_date = DateHandler.get_date_from_string(input())
            print(Communication.due_date, end=" ")
            self.due_date = DateHandler.get_date_from_string(input())
            while True:
                try:
                    print(Communication.recurrence, end=" ")
                    self.recurrence = Recurrence.from_text[input()]
                    break
                except KeyError:
                    print(Communication.invalid_recurrence_valid, *Recurrence.from_text.keys())
        else:
            print(Communication.description, end=" ")
            str_in = input()
            self.description = str_in if str_in != "" else self.description
            print(Communication.do_date, end=" ")
            str_in = input()
            self.do_date = DateHandler.get_date_from_string(str_in) if str_in != "" else self.do_date
            print(Communication.due_date, end=" ")
            str_in = input()
            self.due_date = DateHandler.get_date_from_string(str_in) if str_in != "" else self.due_date
            while True:
                try:
                    print(Communication.recurrence, end=" ")
                    str_in = input()
                    if str_in == "":
                        break
                    self.recurrence = Recurrence.from_text[str_in]
                    break
                except KeyError:
                    print(Communication.invalid_recurrence_valid, *Recurrence.from_text.keys())

    def __str__(self):
        connective = " -- "

        columns = [self.id, self.description]

        do_string = ""
        if self.do_date.year != INVALID_YEAR:
            do_string += self.do_date.strftime(DATE_FORMAT)
            if self.do_date == date.today():
                do_string += connective + Communication.today
            elif self.do_date < date.today():
                do_string += connective + Communication.has_passed
        columns.append(do_string)

        due_string = ""
        if self.due_date.year != INVALID_YEAR:
            due_string += self.due_date.strftime(DATE_FORMAT)
            if self.due_date == date.today():
                due_string += connective + Communication.today
            elif self.due_date < date.today():
                due_string += connective + Communication.overdue
        columns.append(due_string)

        recurrence_string = ""
        if self.recurrence is not None:
            recurrence_string += Recurrence.to_text[self.recurrence]
        columns.append(recurrence_string)

        return TextFormatting.columnize(columns, COLUMN_LENGTHS, PADDING)

class ToDoList:
    def __init__(self):
        self.items : list[ToDoListItem] = []
        self.ids_in_use = []
        self.last_removed: ToDoListItem = None

        self.show_all = False

        self.log_string: str = None

        self.populate()

    def log(self, msg: str):
        self.log_string = msg

    def print_log(self):
        if self.log_string is not None:
            print(self.log_string)
            self.log_string = None

    def populate(self):
        with open(TO_DO_ITEMS_SAVE_FILE, 'r') as f:
            lines = f.readlines()
            for line in lines: # last line is empty
                info = line.strip().split("\\\\")   # info items correspond to ToDoListItem attributes
                to_do_item = ToDoListItem(info[0])
                to_do_item.populate(*info[1:])

                self.items.append(to_do_item)

        self.ids_in_use = [item.id for item in self.items]

    def save(self):
        with open(TO_DO_ITEMS_SAVE_FILE, 'w') as f:
            for to_do_item in self.items:
                save_string = to_do_item.id + "\\\\" + to_do_item.description + "\\\\"
                
                if to_do_item.do_date is None:
                    save_string += "None\\\\"
                else:
                    save_string += to_do_item.do_date.strftime(SAVE_FILE_DATE_FORMAT) + "\\\\"
                
                if to_do_item.due_date is None:
                    save_string += "None\\\\"
                else:
                    save_string += to_do_item.due_date.strftime(SAVE_FILE_DATE_FORMAT)+"\\\\"

                save_string += Recurrence.to_text[to_do_item.recurrence]    # Recurrence handles Nones

                f.write(save_string + "\n")

    def print(self):
        print(
            TextFormatting.columnize(
                [Communication.ID, Communication.description, Communication.do_date, Communication.due_date, Communication.recurrence],
                COLUMN_LENGTHS, PADDING
                ).strip()
        )
        print("-"*(sum(COLUMN_LENGTHS)+PADDING*(len(COLUMN_LENGTHS)-1)))    # Vertical line over all columns
        for to_do_item in self.items:
            if self.show_all:
                print(to_do_item)
            elif to_do_item.recurrence is None or to_do_item.do_date - timedelta(days=2) <= date.today() or to_do_item.due_date - timedelta(days=3) <= date.today():
                print(to_do_item)

        self.show_all = False
        self.print_log()

    def sort(self):
        self.items.sort(key= lambda x: x.due_date)
        self.items.sort(key= lambda x: x.do_date)

    def add_item(self):
        to_do_item = ToDoListItem(self.get_new_id())
        to_do_item.edit(being_created=True)

        self.items.append(to_do_item)
        self.sort()

        self.ids_in_use.append(to_do_item.id)

    def remove_item(self, id: str):
        for i in range(len(self.items)):
            if self.items[i].id == id:
                self.last_removed = self.items.pop(i)
                break
        else:
            self.log(Communication.item_does_not_exist)
            return

        self.ids_in_use.remove(id)

    def undo_remove_item(self):
        if self.last_removed is not None:
            self.items.append(self.last_removed)
            self.sort()

            self.ids_in_use.append(self.last_removed.id)
            self.last_removed = None

    def edit_item(self, id: str):
        item = self.get_item(id)
        if item is not None:
            item.edit()
            self.sort()

    def done_item(self, id: str):
        item = self.get_item(id)
        if item is not None:
            if item.recurrence is not None:
                item.do_date += Recurrence.to_timedelta[item.recurrence]
                item.due_date += Recurrence.to_timedelta[item.recurrence]
                self.sort()
            else:
                self.remove_item(id)

    def finish_recurring_item(self, id: str):
        item = self.get_item(id)
        if item is not None:
            if item.recurrence is not None:
                self.remove_item(id)
            else:
                self.done_item(id)

    def revert_recurring_item(self, id: str):
        item = self.get_item(id)
        if item is not None:
            if item.recurrence is not None:
                item.do_date -= Recurrence.to_timedelta[item.recurrence]
                item.due_date -= Recurrence.to_timedelta[item.recurrence]

    def get_item(self, id: str):
        for item in self.items:
            if item.id == id:
                return item
        else:
            self.log(Communication.item_does_not_exist)
            return None

    def get_new_id(self) -> str:
        n = 1
        while True:
            if str(n) not in self.ids_in_use:
                return str(n)
            n += 1

    def show_all_once(self):
        self.show_all = True

    def remove_all_items(self):
        for i in range(len(self.items)-1, -1, -1):
            self.remove_item(self.items[i].id)


def run_to_do_list():
    to_do_list = ToDoList()

    last_removed: ToDoListItem = None

    quit = False
    while not quit:
        os.system("clear")
        to_do_list.print()
        print("> ", end="")
        command = input()

        if command == "q" or command == "quit" or command == "exit":
            quit = True
        elif command == "":
            continue

        command_args = command.split()

        match command_args[0]:
            case "add" | "+":
                to_do_list.add_item()
            case "done":
                to_do_list.done_item(command_args[1])
            case "undo":
                to_do_list.undo_remove_item()
            case "del" | "remove" | "rm":
                to_do_list.remove_item(command_args[1])
            case "edit":
                to_do_list.edit_item(command_args[1])
            case "finish":
                to_do_list.finish_recurring_item(command_args[1])
            case "revert":
                to_do_list.revert_recurring_item(command_args[1])
            case "show" | "reveal":
                to_do_list.show_all_once()
            case "help":
                print(HELP_STRING)
                print("Hit ENTER to continue")
                input()
            case "delall":
                print("Are you sure? This cannot be undone. [y/N]")
                if input().lower() == "y":
                    to_do_list.remove_all_items()

        to_do_list.save()

if __name__ == '__main__':
    run_to_do_list()
