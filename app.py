import gradio as gr
from datetime import datetime
import copy
from collections import Counter


class Task:
    def __init__(self, title, subject, priority, deadline, status="Belum"):
        self.title = title
        self.subject = subject
        self.priority = priority
        self.deadline = deadline
        self.status = status


# LINKED LIST

class TaskList:
    def __init__(self):
        self.data = []

    def sort(self):
        order = {"High": 1, "Medium": 2, "Low": 3}
        self.data.sort(key=lambda x: (order[x.priority], x.deadline))

    def add(self, task):
        self.data.append(task)
        self.sort()

    def remove(self, title):
        for t in self.data:
            if t.title == title:
                self.data.remove(t)
                return t
        return None

    def find(self, title):
        for t in self.data:
            if t.title == title:
                return t
        return None


# BST

class BSTNode:
    def __init__(self, task):
        self.task = task
        self.left = None
        self.right = None

class DeadlineBST:
    def __init__(self):
        self.root = None

    def insert(self, task):
        self.root = self._insert(self.root, task)

    def _insert(self, node, task):
        if not node:
            return BSTNode(task)
        if task.deadline < node.task.deadline:
            node.left = self._insert(node.left, task)
        else:
            node.right = self._insert(node.right, task)
        return node


# Task List

task_list = TaskList()
bst = DeadlineBST()
undo_stack = []
redo_stack = []



def rebuild_bst():
    bst.root = None
    for t in task_list.data:
        bst.insert(t)

def refresh():
    today = datetime.now()
    rows = []
    for t in task_list.data:
        tag = ""
        if t.status == "Belum" and t.deadline < today:
            tag = "🔴 Overdue"
        elif t.status == "Belum" and 0 <= (t.deadline - today).days <= 3:
            tag = "🟡 Urgent"

        rows.append([
            t.title,
            t.subject,
            t.priority,
            t.deadline.strftime("%d-%m-%Y"),
            t.status,
            tag
        ])
    return rows

def get_statistik():
    total = len(task_list.data)
    selesai = sum(1 for t in task_list.data if t.status == "Selesai")
    pending = total - selesai
    per_mk = Counter(t.subject for t in task_list.data)

    text = f"""Total Tugas : {total}
Selesai     : {selesai}
Pending     : {pending}

Tugas per Mata Kuliah:
"""
    for mk, jml in per_mk.items():
        text += f"- {mk} : {jml}\n"
    return text


# FILTER STATUS

def apply_filter(status_filter):
    if status_filter == "Semua":
        return refresh()

    today = datetime.now()
    rows = []

    for t in task_list.data:
        if t.status != status_filter:
            continue

        tag = ""
        if t.status == "Belum" and t.deadline < today:
            tag = "🔴 Overdue"
        elif t.status == "Belum" and 0 <= (t.deadline - today).days <= 3:
            tag = "🟡 Urgent"

        rows.append([
            t.title,
            t.subject,
            t.priority,
            t.deadline.strftime("%d-%m-%Y"),
            t.status,
            tag
        ])
    return rows


# CORE FUNCTIONS

def tambah(judul, mk, prioritas, deadline):
    try:
        dl = datetime.strptime(deadline, "%d-%m-%Y")
    except:
        return refresh(), get_statistik(), "", "", "", "Belum", "", gr.update(interactive=False), gr.update(interactive=False)

    t = Task(judul, mk, prioritas, dl)
    task_list.add(t)
    bst.insert(t)

    undo_stack.append(("add", copy.deepcopy(t)))
    redo_stack.clear()

    return refresh(), get_statistik(), "", "", "", "Belum", "", gr.update(interactive=False), gr.update(interactive=False)

def edit(selected_title, judul_baru, mk, prioritas, deadline, status):
    if not selected_title:
        return refresh(), get_statistik(), selected_title

    t = task_list.find(selected_title)
    if not t:
        return refresh(), get_statistik(), selected_title

    try:
        dl = datetime.strptime(deadline, "%d-%m-%Y")
    except:
        return refresh(), get_statistik(), selected_title

    old = copy.deepcopy(t)

    t.title = judul_baru
    t.subject = mk
    t.priority = prioritas
    t.deadline = dl
    t.status = status

    undo_stack.append(("edit", old, copy.deepcopy(t)))
    redo_stack.clear()

    task_list.sort()
    rebuild_bst()

    return refresh(), get_statistik(), judul_baru

# DELETE WITH CONFIRM
def show_confirm(selected_title):
    if not selected_title:
        return gr.update(visible=False)
    return gr.update(visible=True)

def hapus_final(selected_title):
    if selected_title:
        t = task_list.remove(selected_title)
        if t:
            undo_stack.append(("delete", copy.deepcopy(t)))
            redo_stack.clear()
            rebuild_bst()

    # AUTO REFRESH + AUTO CLEAR FORM
    return (
        refresh(),
        get_statistik(),
        "", "", "", "Belum", "",
        gr.update(interactive=False),
        gr.update(interactive=False),
        gr.update(visible=False)
    )

def undo():
    if not undo_stack:
        return refresh(), get_statistik()

    action = undo_stack.pop()
    redo_stack.append(action)

    if action[0] == "add":
        task_list.remove(action[1].title)
    elif action[0] == "delete":
        task_list.add(action[1])
    elif action[0] == "edit":
        task_list.remove(action[2].title)
        task_list.add(action[1])

    rebuild_bst()
    return refresh(), get_statistik()

def redo():
    if not redo_stack:
        return refresh(), get_statistik()

    action = redo_stack.pop()
    undo_stack.append(action)

    if action[0] == "add":
        task_list.add(action[1])
    elif action[0] == "delete":
        task_list.remove(action[1].title)
    elif action[0] == "edit":
        task_list.remove(action[1].title)
        task_list.add(action[2])

    rebuild_bst()
    return refresh(), get_statistik()

def pilih_tugas(evt: gr.SelectData):
    idx = evt.index[0]
    t = task_list.data[idx]
    return (
        t.title,
        t.subject,
        t.priority,
        t.deadline.strftime("%d-%m-%Y"),
        t.status,
        t.title,
        gr.update(interactive=True),
        gr.update(interactive=True)
    )


# Interface

with gr.Blocks(title="Sistem Manajemen Tugas Mahasiswa", theme=gr.themes.Soft()) as app:

    gr.Markdown("#  Sistem Manajemen Tugas & To-Do List Mahasiswa")

    selected_title = gr.State("")

    with gr.Row():
        judul = gr.Textbox(label="Judul Tugas")
        mk = gr.Textbox(label="Mata Kuliah")
        prioritas = gr.Dropdown(["High", "Medium", "Low"], label="Prioritas")
        deadline = gr.Textbox(label="Deadline (DD-MM-YYYY)")
        status = gr.Dropdown(["Belum", "Selesai"], label="Status", value="Belum")

    with gr.Row():
        btn_add = gr.Button("➕ Tambah", variant="primary")
        btn_edit = gr.Button("✏️ Edit", interactive=False)
        btn_del = gr.Button("🗑️ Hapus", variant="stop", interactive=False)

    with gr.Row():
        btn_undo = gr.Button("↩️ Undo")
        btn_redo = gr.Button("↪️ Redo")

    gr.Markdown("###  Filter Tugas")
    with gr.Row():
        filter_status = gr.Dropdown(["Semua", "Belum", "Selesai"], value="Semua", label="Status")
        btn_filter = gr.Button("Terapkan Filter")

    table = gr.Dataframe(
        headers=["Judul", "Mata Kuliah", "Prioritas", "Deadline", "Status", "Keterangan"],
        interactive=False
    )

    statistik = gr.Textbox(label=" Statistik", lines=8, interactive=False)

    table.select(
        pilih_tugas,
        None,
        [judul, mk, prioritas, deadline, status, selected_title, btn_edit, btn_del]
    )

    # POPUP
    with gr.Group(visible=False) as confirm_box:
        gr.Markdown("Apakah anda yakin ingin menghapus tugas ini?")
        with gr.Row():
            btn_yes = gr.Button("Ya, Hapus", variant="stop")
            btn_no = gr.Button("Batal")

    
    btn_add.click(
        tambah,
        [judul, mk, prioritas, deadline],
        [table, statistik, judul, mk, deadline, status, selected_title, btn_edit, btn_del]
    )

    btn_edit.click(
        edit,
        [selected_title, judul, mk, prioritas, deadline, status],
        [table, statistik, selected_title]
    )

    btn_del.click(show_confirm, selected_title, confirm_box)

    btn_yes.click(
        hapus_final,
        selected_title,
        [table, statistik, judul, mk, deadline, status, selected_title, btn_edit, btn_del, confirm_box]
    )

    btn_no.click(lambda: gr.update(visible=False), None, confirm_box)

    btn_undo.click(undo, None, [table, statistik])
    btn_redo.click(redo, None, [table, statistik])

    btn_filter.click(apply_filter, filter_status, table)

app.launch(server_name="0.0.0.0", server_port=7860)
