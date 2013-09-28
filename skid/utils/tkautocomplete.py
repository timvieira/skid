from Tkinter import Tk, Entry, Frame, Listbox, StringVar, ACTIVE, END, Frame, SUNKEN


class AutocompleteEntry(Entry):

    def __init__(self, *args, **kwargs):
        Entry.__init__(self, width=100, *args, **kwargs)

        self.focus_set()
        self.pack()

        self.var = self["textvariable"]
        if self.var == '':
            self.var = self["textvariable"] = StringVar()

        self.var.trace('w', self.changed)
        self.bind("<Right>", self.selection)
        self.bind("<Up>", self.up)
        self.bind("<Down>", self.down)
        self.bind("<Return>", self.enter)
        self.lb_up = False
        self.lb = None

    def enter(self, event):
        print event

    def changed(self, name, index, mode):

        if self.var.get() == '':
            if self.lb:
                self.lb.destroy()
            self.lb_up = False
        else:
            words = self.comparison()
            if words:
                if not self.lb_up:
                    self.lb = Listbox(master=root, width=100)

                    self.lb.bind("<Double-Button-1>", self.selection)
                    self.lb.bind("<Right>", self.selection)
                    self.lb.place(x=self.winfo_x(), y=self.winfo_y()+self.winfo_height())
                    self.lb_up = True

                self.lb.delete(0, END)
                for w in words:
                    self.lb.insert(END,w)
            else:
                if self.lb_up:
                    self.lb.destroy()
                    self.lb_up = False

    def selection(self, _):

        if self.lb_up:
            self.var.set(self.lb.get(ACTIVE))
            self.lb.destroy()
            self.lb_up = False
            self.icursor(END)

    def up(self, _):

        if self.lb_up:
            if self.lb.curselection() == ():
                index = '0'
            else:
                index = self.lb.curselection()[0]
            if index != '0':
                self.lb.selection_clear(first=index)
                index = str(int(index)-1)
                self.lb.selection_set(first=index)
                self.lb.activate(index)

    def down(self, _):

        if self.lb_up:
            if self.lb.curselection() == ():
                index = '0'
            else:
                index = self.lb.curselection()[0]
            if index != END:
                self.lb.selection_clear(first=index)
                index = str(int(index)+1)
                self.lb.selection_set(first=index)
                self.lb.activate(index)

    def comparison(self):
        q = self.var.get()
        q = unicode(q.decode('utf8'))
        for hit in searcher.search(qp.parse(q), limit=50):
            if hit['author']:
                yield '%s. "%s"' % (hit['author'], hit['title'])
            else:
                yield hit['title']


from skid.index import open_dir, MultifieldParser, DIRECTORY, NAME

ix = open_dir(DIRECTORY, NAME)
searcher = ix.searcher()
qp = MultifieldParser(fieldnames=['title', 'author', 'tags', 'notes', 'text'],
                      fieldboosts={'title': 5,
                                   'author': 5,
                                   'tags': 3,
                                   'notes': 2,
                                   'text': 1},
                      schema=ix.schema)


if __name__ == '__main__':
    root = Tk()

    frame = Frame(master=root, height=200, width=400, bd=1, relief=SUNKEN)

    entry = AutocompleteEntry(frame)
    entry.grid(row=0, column=0)

    frame.pack(padx=5, pady=5, fill='both', expand=True)

    root.mainloop()
