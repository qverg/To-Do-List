from datetime import date, timedelta
from calendar import monthrange
import os.path
import json

DATE_FORMAT = "%a %d %b"    # e.g. Sat 08 Oct
SAVE_FILE_DATE_FORMAT = "%d/%m/%Y"
TO_DO_ITEMS_SAVE_FILE = os.path.dirname(os.path.abspath(__file__)) + "/todolist_save.json"
SETTINGS_FILE = os.path.dirname(os.path.abspath(__file__)) + "/todolist_settings.json"
LANG_FILE = os.path.dirname(os.path.abspath(__file__)) + "/todolist_lang.json"
INVALID_YEAR = 9999

COLUMN_LENGTHS = (3, 49, 25, 25, 12)
PADDING = 3

SHOW_N_HIDDEN = False

HELP_STRING = """Commands:
 - Basic:
    > 'add' or '+'      Add a to-do list item
    > 'done [ID]'       Mark an item as done (ID is in the leftmost column)
    > 'undo'            Undo delete or mark as done
    > 'edit [ID]'       Edit an item (just press enter to leave a field as is)
 - Sublists
    > 'sub [ID]'        Show sublist for an item
      's [ID]'
    > 'sub'             Close the current sublist (move up in tree), subitems are saved
    > 'home'            Go back to the base list - i.e. close all sublists
 - Recurring items
    > 'finish [ID]'     Mark a recurring item as finished, in effect deleting it
    > 'revert [ID]'     Roll a recurring item back to the previous due date (undo mark as done)
    > 'show'            Show all hidden items (since recurring items with far off due dates are hidden)
 - Meta
    > 'del [ID]'        Remove an item
      'remove [ID]'
      'rm [ID]'
    > 'help'            Seems like you've found this already :-)
    > 'delall'          Delete all items
    > 'q'               Quit
      'quit'
      'exit'
    > 'lang [language]' Change language (requires todolist_lang.json)
    > 'lang'            Show possible languages

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

LANGUAGE = "English"
Communication = {
    "Description: " : "Description: ",
    "Do date:     " : "Do date:     ",
    "Due date:     " : "Due date:     ",
    "Recurrence:  " : "Recurrence:  ",
    "Invalid recurrence. Valid:" : "Invalid recurrence. Valid:",
    "Item does not exist." : "Item does not exist.",
    "Today!" : "Today!",
    "Has passed!" : "Has passed!",
    "OVERDUE!" : "OVERDUE!",
    "ID" : "ID",
    "Are you sure? This cannot be undone. " : "Are you sure? This cannot be undone. ",
    "weekly" : "weekly",
    "monthly" : "monthly",
    "daily" : "daily",
    "Language not found." : "Language not found."
}

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
    def columnize(items: list[str], collengths: tuple[int] | int, padding: int, justify="left", end_newline=True) -> str:
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

        if not end_newline:
            out = out[:-1]
        return out

class Recurrence:
    WEEKLY = 1
    MONTHLY = 2
    DAILY = 3

    to_timedelta = {
        WEEKLY : timedelta(weeks=1),
        MONTHLY : timedelta(days=monthrange(date.today().year, date.today().month)[1]),
        DAILY : timedelta(days=1)
    }

    @staticmethod
    def from_text(rec_in: str):
        if rec_in == Communication["weekly"] : return Recurrence.WEEKLY
        if rec_in == Communication["monthly"] : return Recurrence.MONTHLY
        if rec_in == Communication["daily"] : return Recurrence.DAILY
        return None

    @staticmethod
    def get_valid():
        return Communication["weekly"], Communication["monthly"], Communication["daily"], "None", ""

    @staticmethod
    def to_text(rec_in):
        match rec_in:
            case Recurrence.WEEKLY : return Communication["weekly"]
            case Recurrence.MONTHLY : return Communication["monthly"]
            case Recurrence.DAILY : return Communication["daily"]
        return "None"



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

class ToDoListItem:
    def __init__(self, id: str) -> None:
        self.id: str = id
        self.description: str = ""
        self.do_date: date = None
        self.due_date: date = None
        self.recurrence: Recurrence = None
        
        self._sublist: ToDoList = ToDoList({})

    @property
    def sublist(self):
        return self._sublist

    def populate(
            self,
            description: str,
            do_date_str: str,
            due_date_str: str,
            recurrence_str: str,
            sublist: dict
        ):
        self.description = description
        self.do_date = DateHandler.get_date_from_string(do_date_str)
        self.due_date = DateHandler.get_date_from_string(due_date_str)
        self.recurrence = Recurrence.from_text(recurrence_str)
        self._sublist = ToDoList(sublist)

    def edit(self, being_created = False, desc=None):
        if being_created:
            if desc is None:
                print(Communication["Description: "], end=" ")
                self.description = input()
            else:
                self.description = desc
            print(Communication["Do date:     "], end=" ")
            self.do_date = DateHandler.get_date_from_string(input())
            print(Communication["Due date:     "], end=" ")
            self.due_date = DateHandler.get_date_from_string(input())
            while True:
                print(Communication["Recurrence:  "], end=" ")
                rec_in = input().strip()
                if rec_in in Recurrence.get_valid():
                    self.recurrence = Recurrence.from_text(rec_in)
                    break
                else:
                    print(Communication["Invalid recurrence. Valid:"], *Recurrence.get_valid())
    
        else:
            print(Communication["Description: "], end=" ")
            str_in = input()
            self.description = str_in if str_in != "" else self.description
            print(Communication["Do date:     "], end=" ")
            str_in = input()
            self.do_date = DateHandler.get_date_from_string(str_in) if str_in != "" else self.do_date
            print(Communication["Due date:     "], end=" ")
            str_in = input()
            self.due_date = DateHandler.get_date_from_string(str_in) if str_in != "" else self.due_date

            while True:
                print(Communication["Recurrence:  "], end=" ")
                rec_in = input().strip()
                if rec_in == "":
                    break
                if rec_in in Recurrence.get_valid():
                    self.recurrence = Recurrence.from_text(rec_in)
                    break
                else:
                    print(Communication["Invalid recurrence. Valid:"], *Recurrence.get_valid())

    def to_string(self, generation=0, in_hierarchy=False):
        connective = " -- "

        id_string = self.id if not in_hierarchy else ""
        descr_prefix = ""
        if generation > 0:
            descr_prefix = "   "*(generation-1) + "-> "

        columns = [id_string, descr_prefix+self.description]

        do_string = ""
        if self.do_date.year != INVALID_YEAR:
            do_string += self.do_date.strftime(DATE_FORMAT)
            if self.do_date == date.today():
                do_string += connective + Communication["Today!"]
            elif self.do_date < date.today():
                do_string += connective + Communication["Has passed!"]
        columns.append(do_string)

        due_string = ""
        if self.due_date.year != INVALID_YEAR:
            due_string += self.due_date.strftime(DATE_FORMAT)
            if self.due_date == date.today():
                due_string += connective + Communication["Today!"]
            elif self.due_date < date.today():
                due_string += connective + Communication["OVERDUE!"]
        columns.append(due_string)

        recurrence_string = ""
        if self.recurrence is not None:
            recurrence_string += Recurrence.to_text(self.recurrence)
        columns.append(recurrence_string)

        out = TextFormatting.columnize(columns, COLUMN_LENGTHS, PADDING, end_newline=False)
        if not in_hierarchy:
            out += "\n"
            if self.sublist.items:
                prefix = "   "*generation + "->"
                out += TextFormatting.columnize(["","   "*generation + "-> ...","","",""], COLUMN_LENGTHS, PADDING, end_newline=True)
        return out

class ToDoList:
    def __init__(self, save_dict: dict):
        self.items : list[ToDoListItem] = []
        self.ids_in_use = []
        self.last_removed: ToDoListItem = None

        self.show_all = False

        self.log_string: str = None

        self.populate(save_dict)

    def log(self, message: str) -> None:
        if self.log_string is None:
            self.log_string = message
        else:
            self.log_string += "\n"+message

    def print_log(self):
        if self.log_string is not None:
            print(self.log_string)
            self.log_string = None

    def populate(self, save_dict: dict):
        self.ids_in_use = []
        for item_id, item_info in save_dict.items():
            to_do_item = ToDoListItem(item_id)

            if item_info["do_date"] == "None":
                item_info["do_date"] = None
            if item_info["due_date"] == "None":
                item_info["due_date"] = None
            
            to_do_item.populate(
                item_info["description"],
                item_info["do_date"],
                item_info["due_date"],
                item_info["recurrence"],
                item_info["sublist"]
            )

            self.items.append(to_do_item)
            self.ids_in_use.append(item_id)

    def get_save_dict(self):
        save_dict = {}
        for to_do_item in self.items:
            save_dict[to_do_item.id] = {
                "description" : to_do_item.description,
                "do_date" : to_do_item.do_date.strftime(SAVE_FILE_DATE_FORMAT) if to_do_item.do_date is not None else "None",
                "due_date" : to_do_item.due_date.strftime(SAVE_FILE_DATE_FORMAT) if to_do_item.due_date is not None else "None",
                "recurrence" : Recurrence.to_text(to_do_item.recurrence),
                "sublist" : to_do_item.sublist.get_save_dict()
            }
            
        return save_dict

    def sort(self):
        self.items.sort(key= lambda x: x.due_date)
        self.items.sort(key= lambda x: x.do_date)

    def add_item(self, desc=None):
        to_do_item = ToDoListItem(self.get_new_id())
        to_do_item.edit(being_created=True, desc=desc)

        self.items.append(to_do_item)
        self.sort()

        self.ids_in_use.append(to_do_item.id)

    def remove_item(self, id: str):
        for i in range(len(self.items)):
            if self.items[i].id == id:
                self.last_removed = self.items.pop(i)
                break
        else:
            for i in range(len(self.items)):
                if self.items[i].description == id:
                    id = self.items[i].id
                    self.last_removed = self.items.pop(i)
                    break
            else:
                self.log(Communication["Item does not exist."])
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
            for item in self.items:
                if item.description == id:
                    return item
            else:
                self.log(Communication["Item does not exist."])
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

class ToDoListManager:
    def __init__(self) -> None:
        self._base: ToDoList = None
        self._stack: list[ToDoListItem] = []
        self._show_all = False

        self.populate()

    @property
    def top(self) -> ToDoList:
        if len(self._stack) > 0:
            return self._stack[-1].sublist
        return self._base

    def populate(self) -> None:
        with open(TO_DO_ITEMS_SAVE_FILE, 'r') as f:
            save_dict = json.load(f)
        
        self._base = ToDoList(save_dict)

    def save(self) -> None:
        save_dict = self._base.get_save_dict()
        with open(TO_DO_ITEMS_SAVE_FILE, 'w') as f:
            json.dump(save_dict, f, ensure_ascii=False, indent=4)


    def push_sublist(self, id: str) -> None:
        item = self.top.get_item(id)
        if item is not None:
            self._stack.append(item)

    def pop_sublist(self) -> None:
        if len(self._stack) > 0:
            self._stack.pop(-1)

    def go_home(self) -> None:
        self._stack = []

    def show_all_once(self) -> None:
        self._show_all = True

    def print(self) -> None:
        print(
            TextFormatting.columnize(
                [Communication["ID"], Communication["Description: "], Communication["Do date:     "], Communication["Due date:     "], Communication["Recurrence:  "]],
                COLUMN_LENGTHS, PADDING
                ).strip()
        )

        width = sum(COLUMN_LENGTHS)+PADDING*(len(COLUMN_LENGTHS)-1)
        print("-"*width)    # Vertical line over all columns
        
        generation = 0
        for parent_item in self._stack:
            print(parent_item.to_string(generation, True))
            generation += 1
        print("")   # newline

        hidden_items = 0
        for to_do_item in self.top.items:
            if self._show_all:
                print(to_do_item.to_string(generation))
            elif to_do_item.recurrence is None or to_do_item.do_date - timedelta(days=2) <= date.today() or to_do_item.due_date - timedelta(days=3) <= date.today():
                print(to_do_item.to_string(generation))
            else:
                hidden_items += 1

        if SHOW_N_HIDDEN and hidden_items != 0:
            print(f"({hidden_items} {Communication['hidden']}) \n".rjust(width))

        self._show_all = False
        self.top.print_log()


def run_to_do_list():
    global Communication

    to_do_list = ToDoListManager()

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
                if command[4:] == "":  # without "add "
                    to_do_list.top.add_item()
                else:
                    to_do_list.top.add_item(command[4:])
            case "done":
                to_do_list.top.done_item(command_args[1])
            case "undo":
                to_do_list.top.undo_remove_item()
            case "sub" | "s":
                if len(command_args) == 1:
                    to_do_list.pop_sublist()
                else:
                    to_do_list.push_sublist(command_args[1])
            case "home":
                to_do_list.go_home()
            case "del" | "remove" | "rm":
                to_do_list.top.remove_item(command_args[1])
            case "edit":
                to_do_list.top.edit_item(command_args[1])
            case "finish":
                to_do_list.top.finish_recurring_item(command_args[1])
            case "revert":
                to_do_list.top.revert_recurring_item(command_args[1])
            case "show" | "reveal":
                to_do_list.show_all_once()
            case "help":
                to_do_list.top.log(HELP_STRING)
            case "delall":
                print(Communication["Are you sure? This cannot be undone. "] + "[y/N]")
                if input().lower() == "y":
                    to_do_list.top.remove_all_items()
            case "lang":
                try:
                    with open(LANG_FILE, "r", encoding="utf-8") as lang_file:
                        Communication = json.load(lang_file)[command_args[1]]

                except FileNotFoundError:
                    to_do_list.top.log("Missing todolist_lang.json")

                except KeyError:
                    to_do_list.top.log(Communication["Language not found."])

                except IndexError:
                    with open(LANG_FILE, "r", encoding="utf-8") as lang_file:
                        languages = ""
                        for language in json.load(lang_file).keys():
                            languages += language + "\n"
                        to_do_list.top.log(languages.strip())

                else:
                    try:
                        with open(SETTINGS_FILE, "r", encoding="utf-8") as settings_file:
                            settings = json.load(settings_file)

                        settings["language"] = command_args[1]

                        with open(SETTINGS_FILE, "w", encoding="utf-8") as settings_file:
                            json.dump(settings, settings_file, ensure_ascii=False, indent=4)
                    except FileNotFoundError:
                        pass

        to_do_list.save()

if __name__ == '__main__':
    # create save file (with {} for json loading) if it doesn't exist
    with open(TO_DO_ITEMS_SAVE_FILE, "a+") as f:
        f.seek(0)
        in_f = f.read()
        assert type(in_f) == str
        if in_f.strip() == "":
            f.write("{}")

    # load settings
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as settings_file:
            settings = json.load(settings_file)
            try:
                COLUMN_LENGTHS = tuple(settings["column_widths_in_characters"])
                PADDING = settings["column_padding_in_characters"]
                LANGUAGE = settings["language"]
                SHOW_N_HIDDEN = settings["show_number_of_hidden_items"]
            except KeyError:
                pass
    except FileNotFoundError:
        pass
    
    try:
        with open(LANG_FILE, "r", encoding="utf-8") as lang_file:
            Communication = json.load(lang_file)[LANGUAGE]

    except FileNotFoundError:
        pass

    run_to_do_list()
