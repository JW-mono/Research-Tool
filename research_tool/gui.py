"""Tkinter GUI: a search bar for a research topic, with results (title,
metadata, and the full introduction/results/conclusion summary) shown
directly in a scrollable report -- no extra click needed to see them.
"""

import csv
import json
import queue
import threading
import tkinter as tk
import webbrowser
from tkinter import ttk, filedialog, messagebox

from research_tool.cli import build_records

ACCESS_COLORS = {
    "Open Access (free for anyone)": "#1a7f37",
    "TU Delft subscription (likely)": "#9a6700",
    "Not covered - check Library / request via ILL": "#cf222e",
    "Unknown publisher - check Library manually": "#57606a",
}


class ResearchToolApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Research Tool")
        self.root.geometry("1000x750")

        self.records = []
        self._work_queue = queue.Queue()
        self._link_targets = {}
        self._link_counter = 0

        self._build_widgets()

    # ---- UI construction -------------------------------------------------

    def _build_widgets(self):
        search_frame = ttk.Frame(self.root, padding=10)
        search_frame.pack(fill="x")

        ttk.Label(search_frame, text="Topic:").pack(side="left")
        self.topic_var = tk.StringVar()
        topic_entry = ttk.Entry(search_frame, textvariable=self.topic_var, width=45)
        topic_entry.pack(side="left", padx=(5, 15))
        topic_entry.bind("<Return>", lambda e: self.on_search())
        topic_entry.focus_set()

        ttk.Label(search_frame, text="Max results:").pack(side="left")
        self.limit_var = tk.IntVar(value=15)
        ttk.Spinbox(search_frame, from_=1, to=100, width=5, textvariable=self.limit_var).pack(
            side="left", padx=(5, 15)
        )

        self.sort_var = tk.StringVar(value="relevance")
        ttk.Label(search_frame, text="Sort:").pack(side="left")
        ttk.Combobox(
            search_frame, textvariable=self.sort_var, state="readonly", width=12,
            values=["relevance", "access"],
        ).pack(side="left", padx=(5, 15))

        self.search_button = ttk.Button(search_frame, text="Search", command=self.on_search)
        self.search_button.pack(side="left")

        ttk.Button(search_frame, text="Export CSV...", command=self.export_csv).pack(side="right", padx=(5, 0))
        ttk.Button(search_frame, text="Export JSON...", command=self.export_json).pack(side="right")

        self.status_var = tk.StringVar(value="Enter a topic and press Search.")
        ttk.Label(self.root, textvariable=self.status_var, padding=(10, 4)).pack(fill="x")

        # Scrollable report area: every result's title + summary is visible
        # directly, no click required.
        report_frame = ttk.Frame(self.root)
        report_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # "Segoe UI" has broader Unicode coverage (en/em dashes, accents) than
        # TkDefaultFont, which on Windows can fall back to a font that renders
        # some punctuation from publication metadata as a tofu box.
        base_font = ("Segoe UI", 10)
        self.report_text = tk.Text(
            report_frame, wrap="word", state="disabled",
            font=base_font, padx=10, pady=10,
        )
        scrollbar = ttk.Scrollbar(report_frame, orient="vertical", command=self.report_text.yview)
        self.report_text.configure(yscrollcommand=scrollbar.set)
        self.report_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.report_text.tag_configure("title", font=("Segoe UI", 12, "bold"))
        self.report_text.tag_configure("meta", foreground="#57606a")
        self.report_text.tag_configure("section", font=("Segoe UI", 10, "bold"))
        self.report_text.tag_configure("link", foreground="#0969da", underline=True)
        self.report_text.tag_configure("sep", foreground="#d0d7de")
        self.report_text.tag_configure("notice", foreground="#57606a", font=("Segoe UI", 10, "italic"))
        self.report_text.tag_configure("error", foreground="#cf222e")
        for status, color in ACCESS_COLORS.items():
            self.report_text.tag_configure(status, foreground=color, font=("Segoe UI", 9, "bold"))

    # ---- Search ------------------------------------------------------------

    def on_search(self):
        topic = self.topic_var.get().strip()
        if not topic:
            messagebox.showinfo("Research Tool", "Enter a research topic first.")
            return

        self.search_button.config(state="disabled")
        self.status_var.set(f'Searching for "{topic}"...')
        self._set_report_text("")
        self._link_targets.clear()

        limit = self.limit_var.get()
        sort_mode = self.sort_var.get()

        thread = threading.Thread(
            target=self._search_worker, args=(topic, limit, sort_mode), daemon=True
        )
        thread.start()
        self.root.after(100, self._poll_worker)

    def _search_worker(self, topic, limit, sort_mode):
        try:
            records = build_records(topic, limit, mailto=None)
            if sort_mode == "access":
                priority = {
                    "Open Access (free for anyone)": 0,
                    "TU Delft subscription (likely)": 1,
                    "Unknown publisher - check Library manually": 2,
                    "Not covered - check Library / request via ILL": 3,
                }
                records.sort(key=lambda r: priority.get(r["access_status"], 99))
            self._work_queue.put(("ok", records))
        except Exception as exc:
            self._work_queue.put(("error", str(exc)))

    def _poll_worker(self):
        try:
            status, payload = self._work_queue.get_nowait()
        except queue.Empty:
            self.root.after(100, self._poll_worker)
            return

        self.search_button.config(state="normal")
        if status == "error":
            self.status_var.set("Search failed.")
            messagebox.showerror("Research Tool", f"Error fetching publications:\n{payload}")
            return

        self.records = payload
        if not self.records:
            self.status_var.set("No results found.")
            return

        accessible = sum(
            1 for r in self.records
            if r["access_status"] in ("Open Access (free for anyone)", "TU Delft subscription (likely)")
        )
        summarized = sum(1 for r in self.records if r["summary"]["status"] == "ok")
        status_msg = f"{len(self.records)} results - {accessible} likely accessible - {summarized} summarized"
        errored = sum(1 for r in self.records if r["summary"]["status"] == "error")
        if errored:
            status_msg += f" - {errored} summary errors (see report)"
        self.status_var.set(status_msg + ".")
        self._render_report()

    # ---- Report rendering --------------------------------------------------

    def _set_report_text(self, text):
        self.report_text.config(state="normal")
        self.report_text.delete("1.0", "end")
        if text:
            self.report_text.insert("end", text)
        self.report_text.config(state="disabled")

    def _render_report(self):
        t = self.report_text
        t.config(state="normal")
        t.delete("1.0", "end")

        for i, r in enumerate(self.records):
            authors = ", ".join(a for a in r["authors"] if a) or "Unknown authors"
            t.insert("end", f"{r['title']}\n", "title")
            t.insert("end", f"{authors} ({r['year'] or 'n.d.'})\n", "meta")
            t.insert(
                "end",
                f"Journal: {r['journal'] or 'Unknown'}    Publisher: {r['publisher'] or 'Unknown'}\n",
                "meta",
            )
            t.insert("end", f"{r['access_status']}\n", r["access_status"])
            if r["doi"]:
                t.insert("end", f"DOI: {r['doi']}\n", "meta")
            if r["is_oa"] and r["oa_url"]:
                self._insert_link(t, r["oa_url"], "Open full text")
            t.insert("end", "\n")

            status = r["summary"]["status"]
            if status == "no_abstract":
                t.insert("end", "OpenAlex has no abstract for this result -- nothing to summarize.\n", "notice")
            elif status == "error":
                t.insert("end", f"Summary unavailable -- Claude API error: {r['summary']['error']}\n", "error")
            else:
                for label, key in (("Introduction", "introduction"), ("Results", "results"), ("Conclusion", "conclusion")):
                    t.insert("end", f"{label}: ", "section")
                    t.insert("end", (r["summary"][key] or "(Claude found nothing to say for this section)") + "\n")

            if i != len(self.records) - 1:
                t.insert("end", "\n" + ("-" * 100) + "\n\n", "sep")

        t.config(state="disabled")

    def _insert_link(self, text_widget, url, label):
        tag = f"link_{self._link_counter}"
        self._link_counter += 1
        self._link_targets[tag] = url
        text_widget.tag_configure(tag, foreground="#0969da", underline=True)
        text_widget.tag_bind(tag, "<Button-1>", lambda e, u=url: webbrowser.open(u))
        text_widget.tag_bind(tag, "<Enter>", lambda e: text_widget.config(cursor="hand2"))
        text_widget.tag_bind(tag, "<Leave>", lambda e: text_widget.config(cursor=""))
        text_widget.insert("end", label + "\n", tag)

    # ---- Export ------------------------------------------------------------

    def export_csv(self):
        if not self._require_records():
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not path:
            return
        fields = [
            "title", "year", "authors", "journal", "publisher", "doi",
            "access_status", "oa_url", "summary_status", "summary_error",
            "summary_introduction", "summary_results", "summary_conclusion",
        ]
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            for r in self.records:
                writer.writerow({
                    "title": r["title"], "year": r["year"],
                    "authors": "; ".join(a for a in r["authors"] if a),
                    "journal": r["journal"], "publisher": r["publisher"], "doi": r["doi"],
                    "access_status": r["access_status"], "oa_url": r["oa_url"],
                    "summary_status": r["summary"]["status"],
                    "summary_error": r["summary"]["error"] or "",
                    "summary_introduction": r["summary"]["introduction"],
                    "summary_results": r["summary"]["results"],
                    "summary_conclusion": r["summary"]["conclusion"],
                })
        self.status_var.set(f"Wrote CSV to {path}")

    def export_json(self):
        if not self._require_records():
            return
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.records, f, indent=2, ensure_ascii=False)
        self.status_var.set(f"Wrote JSON to {path}")

    def _require_records(self):
        if not self.records:
            messagebox.showinfo("Research Tool", "Run a search first.")
            return False
        return True


def main():
    root = tk.Tk()
    ResearchToolApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
