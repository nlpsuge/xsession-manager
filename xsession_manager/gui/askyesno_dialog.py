import tkinter as tk
from tkinter import Button


def create_askyesno_dialog(label_text: str, choose_yes_if_timeout: int=10):

    class AskYesNoDialog(tk.Toplevel):

        b_yes: Button
        label: tk.Label

        def __init__(self, parent, label_content, yes_button_text):
            tk.Toplevel.__init__(self, parent)
            self.label = tk.Label(self, text=label_content)
            self.label.grid(row=0, column=0, columnspan=2, padx=50, pady=10)

            b_yes = tk.Button(self, text=yes_button_text, command=self.yes, width=8)
            self.b_yes = b_yes
            b_yes.grid(row=1, column=0, padx=10, pady=10)
            b_no = tk.Button(self, text="No", command=self.no, width=8)
            b_no.grid(row=1, column=1, padx=10, pady=10)

            self.answer = None
            self.protocol("WM_DELETE_WINDOW", self.no)

        def yes(self, event=None):
            self.answer = "Yes"
            self.destroy()

        def no(self, event=None):
            self.answer = "No"
            self.destroy()

    def _countdown(d: AskYesNoDialog,
                   yes_button_text_with_countdown_template,
                   count=choose_yes_if_timeout):
        d.b_yes['text'] = yes_button_text_with_countdown_template % count
        root.after(1000, _countdown, d, yes_button_text_with_countdown_template, count - 1)

    def popup_question_dialog():
        yes_button_text_with_countdown_template = 'Yes(%ds)'
        if choose_yes_if_timeout:
            yes_button_text = yes_button_text_with_countdown_template % choose_yes_if_timeout
        else:
            yes_button_text = 'Yes'
        d = AskYesNoDialog(root, label_text, yes_button_text)
        # Quit the dialog by pressing Esc, the answer will be no
        d.bind('<Escape>', d.no)
        d.bind('<Control-q>', d.no)
        # Focus yes button so that we can press space key to choose yes quickly
        d.b_yes.focus_set()
        _place_in_center(d)
        # Choose yes if timeout
        root.after(choose_yes_if_timeout * 1000, d.yes)
        # Countdown at 1-second intervals
        root.after(0, _countdown, d, yes_button_text_with_countdown_template)
        # Display the dialog in the center of screen
        root.wait_window(d)
        print('Your answer is: %s' % d.answer)
        return d.answer

    root = tk.Tk()
    root.title('Question')
    root.withdraw()
    answer = popup_question_dialog()
    if answer and answer == 'Yes':
        return True
    return False


def _place_in_center(root):
    # Gets the requested values of the height and width.
    window_width = root.winfo_reqwidth()
    window_height = root.winfo_reqheight()
    # Gets both half the screen width/height and window width/height
    position_right = int(root.winfo_screenwidth() / 2 - window_width / 2)
    position_down = int(root.winfo_screenheight() / 2 - window_height / 2)
    # Positions the window in the center of the page.
    root.geometry("+%d+%d" % (position_right, position_down))
