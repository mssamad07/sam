"""
Windows Desktop Heads-Up Display (HUD) Interface for Sam.
Provides an elegant, non-intrusive floating overlay with real-time status,
speech transcriptions, response bubbles, and Tier 2/3 permission confirmations.
"""
import asyncio
import tkinter as tk
from typing import Any

from sam_clients.windows_hud.hud_client import HUDClient


class HUDWindow:
    """
    Desktop HUD interface rendered using Tkinter with a modern dark theme.
    Can run in standalone mode or be embedded within an async loop.
    """

    STATE_COLORS = {
        "idle": "#10B981",              # Emerald green
        "wake_detected": "#06B6D4",     # Cyan
        "listening": "#3B82F6",         # Blue
        "processing": "#F59E0B",        # Amber
        "waiting_for_permission": "#EF4444",  # Coral red
        "speaking": "#8B5CF6",          # Violet
        "interrupted": "#F97316",       # Orange
        "error": "#DC2626",             # Red
    }

    def __init__(self, hud_client: HUDClient | None = None, loop: asyncio.AbstractEventLoop | None = None) -> None:
        self.client = hud_client or HUDClient()
        self.loop = loop
        self.root: tk.Tk | None = None
        self._status_label = None
        self._status_dot = None
        self._transcription_label = None
        self._response_label = None
        self._permission_frame = None
        self._permission_desc = None
        self._entry = None

    def build_ui(self) -> tk.Tk:
        """Construct the Tkinter HUD window."""
        self.root = tk.Tk()
        self.root.title("Sam AI Assistant")
        self.root.geometry("460x320")
        self.root.minsize(400, 260)
        self.root.configure(bg="#121214")

        # Top status header
        header = tk.Frame(self.root, bg="#18181b", padx=14, pady=10)
        header.pack(fill=tk.X)

        self._status_canvas = tk.Canvas(header, width=14, height=14, bg="#18181b", highlightthickness=0)
        self._status_canvas.pack(side=tk.LEFT, padx=(0, 8))
        self._status_dot = self._status_canvas.create_oval(2, 2, 12, 12, fill=self.STATE_COLORS["idle"], outline="")

        self._status_label = tk.Label(
            header,
            text="Sam: Ready",
            font=("Segoe UI", 10, "bold"),
            bg="#18181b",
            fg="#F4F4F5",
        )
        self._status_label.pack(side=tk.LEFT)

        # Quick Actions in header
        btn_mute = tk.Button(
            header,
            text="Mute",
            font=("Segoe UI", 8),
            bg="#27272a",
            fg="#E4E4E7",
            activebackground="#3f3f46",
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
            padx=6,
            pady=2,
            command=self._on_mute_clicked,
        )
        btn_mute.pack(side=tk.RIGHT, padx=4)

        btn_stop = tk.Button(
            header,
            text="Stop",
            font=("Segoe UI", 8),
            bg="#27272a",
            fg="#E4E4E7",
            activebackground="#3f3f46",
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
            padx=6,
            pady=2,
            command=self._on_stop_clicked,
        )
        btn_stop.pack(side=tk.RIGHT, padx=4)

        # Content Frame
        content_frame = tk.Frame(self.root, bg="#121214", padx=14, pady=10)
        content_frame.pack(fill=tk.BOTH, expand=True)

        # Transcription Display
        lbl_heard = tk.Label(
            content_frame,
            text="HEARD",
            font=("Segoe UI", 8, "bold"),
            bg="#121214",
            fg="#71717A",
        )
        lbl_heard.pack(anchor=tk.W)

        self._transcription_label = tk.Label(
            content_frame,
            text="Waiting for wake word ('Hey Sam')...",
            font=("Segoe UI", 10, "italic"),
            bg="#18181b",
            fg="#A1A1AA",
            anchor=tk.W,
            padx=8,
            pady=6,
            wraplength=420,
            justify=tk.LEFT,
        )
        self._transcription_label.pack(fill=tk.X, pady=(2, 8))

        # Response Display
        lbl_sam = tk.Label(
            content_frame,
            text="SAM",
            font=("Segoe UI", 8, "bold"),
            bg="#121214",
            fg="#71717A",
        )
        lbl_sam.pack(anchor=tk.W)

        self._response_label = tk.Label(
            content_frame,
            text="I'm here, Boss. How can I help you today?",
            font=("Segoe UI", 10),
            bg="#27272a",
            fg="#FAFAFA",
            anchor=tk.W,
            padx=8,
            pady=6,
            wraplength=420,
            justify=tk.LEFT,
        )
        self._response_label.pack(fill=tk.X, pady=(2, 8))

        # Permission Card (initially hidden)
        self._permission_frame = tk.Frame(content_frame, bg="#451a1a", padx=8, pady=6)
        self._permission_desc = tk.Label(
            self._permission_frame,
            text="Action requires approval: ",
            font=("Segoe UI", 9, "bold"),
            bg="#451a1a",
            fg="#FECACA",
            wraplength=300,
            justify=tk.LEFT,
        )
        self._permission_desc.pack(side=tk.LEFT, fill=tk.X, expand=True)

        btn_approve = tk.Button(
            self._permission_frame,
            text="Approve",
            font=("Segoe UI", 8, "bold"),
            bg="#059669",
            fg="#FFFFFF",
            relief=tk.FLAT,
            command=self._on_approve_clicked,
        )
        btn_approve.pack(side=tk.RIGHT, padx=4)

        btn_deny = tk.Button(
            self._permission_frame,
            text="Deny",
            font=("Segoe UI", 8),
            bg="#DC2626",
            fg="#FFFFFF",
            relief=tk.FLAT,
            command=self._on_deny_clicked,
        )
        btn_deny.pack(side=tk.RIGHT, padx=4)

        # Bottom Input Field
        input_frame = tk.Frame(self.root, bg="#18181b", padx=10, pady=8)
        input_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self._entry = tk.Entry(
            input_frame,
            font=("Segoe UI", 10),
            bg="#27272a",
            fg="#FFFFFF",
            insertbackground="#FFFFFF",
            relief=tk.FLAT,
        )
        self._entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6), ipady=3)
        self._entry.bind("<Return>", lambda e: self._on_send_clicked())

        btn_send = tk.Button(
            input_frame,
            text="Send",
            font=("Segoe UI", 9, "bold"),
            bg="#3B82F6",
            fg="#FFFFFF",
            activebackground="#2563EB",
            relief=tk.FLAT,
            command=self._on_send_clicked,
        )
        btn_send.pack(side=tk.RIGHT)

        return self.root

    def update_state(self, new_state: str) -> None:
        """Update status dot color and label."""
        if not self.root:
            return
        color = self.STATE_COLORS.get(new_state.lower(), "#9CA3AF")
        label_text = f"Sam: {new_state.capitalize().replace('_', ' ')}"
        self._status_canvas.itemconfig(self._status_dot, fill=color)
        self._status_label.config(text=label_text)

    def update_transcription(self, text: str) -> None:
        """Update live transcription."""
        if not self.root or not self._transcription_label:
            return
        self._transcription_label.config(text=text)

    def update_response(self, text: str) -> None:
        """Update Sam's response bubble."""
        if not self.root or not self._response_label:
            return
        self._response_label.config(text=text)

    def show_permission_prompt(self, request_info: dict[str, Any]) -> None:
        """Display Tier 2/3 confirmation prompt."""
        if not self.root or not self._permission_frame:
            return
        tool = request_info.get("tool_name", "Action")
        desc = f"Authorize: {tool}?"
        self._permission_desc.config(text=desc)
        self._permission_frame.pack(fill=tk.X, pady=(4, 8))

    def hide_permission_prompt(self) -> None:
        """Hide permission card."""
        if self._permission_frame:
            self._permission_frame.pack_forget()

    def _on_send_clicked(self) -> None:
        if not self._entry:
            return
        text = self._entry.get().strip()
        if not text:
            return
        self._entry.delete(0, tk.END)
        self.update_transcription(text)
        self.update_state("processing")

        if self.loop and self.client.is_connected:
            asyncio.run_coroutine_threadsafe(self._async_send(text), self.loop)

    async def _async_send(self, text: str) -> None:
        try:
            res = await self.client.send_message(text)
            resp_text = res.get("response_text", "")
            self.root.after(0, lambda: self.update_response(resp_text))
            self.root.after(0, lambda: self.update_state("speaking"))
        except Exception as e:
            err_msg = f"Error: {e}"
            self.root.after(0, lambda msg=err_msg: self.update_response(msg))
            self.root.after(0, lambda: self.update_state("error"))

    def _on_mute_clicked(self) -> None:
        self.update_transcription("[Microphone Muted]")

    def _on_stop_clicked(self) -> None:
        self.update_response("[Playback Stopped]")
        self.update_state("idle")

    def _on_approve_clicked(self) -> None:
        self.hide_permission_prompt()
        if self.client.active_permission_request and self.loop:
            token = self.client.active_permission_request.get("token", "")
            asyncio.run_coroutine_threadsafe(self.client.resolve_permission(token, approved=True), self.loop)

    def _on_deny_clicked(self) -> None:
        self.hide_permission_prompt()
        if self.client.active_permission_request and self.loop:
            token = self.client.active_permission_request.get("token", "")
            asyncio.run_coroutine_threadsafe(self.client.resolve_permission(token, approved=False), self.loop)
