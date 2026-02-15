import customtkinter as ctk


class CollapsibleSection(ctk.CTkFrame):
    """Reusable collapsible panel with toggle button and content frame."""

    def __init__(self, master, title: str, expanded: bool = False, **kwargs):
        super().__init__(master, **kwargs)
        self._title = title
        self._is_expanded = expanded

        # Header toggle button
        arrow = "\u25bc" if expanded else "\u25b6"
        self._toggle_btn = ctk.CTkButton(
            self,
            text=f"{arrow}  {title}",
            command=self.toggle,
            fg_color="transparent",
            text_color=("gray10", "gray90"),
            anchor="w",
            font=ctk.CTkFont(size=15, weight="bold"),
            hover_color=("gray85", "gray25"),
            height=36,
        )
        self._toggle_btn.pack(fill="x", padx=4, pady=(4, 0))

        # Content frame (hidden by default)
        self._content_frame = ctk.CTkFrame(self, fg_color="transparent")
        if expanded:
            self._content_frame.pack(fill="both", expand=True, padx=8, pady=(4, 8))

    @property
    def content_frame(self) -> ctk.CTkFrame:
        return self._content_frame

    def toggle(self):
        if self._is_expanded:
            self._content_frame.pack_forget()
            self._toggle_btn.configure(text=f"\u25b6  {self._title}")
        else:
            self._content_frame.pack(fill="both", expand=True, padx=8, pady=(4, 8))
            self._toggle_btn.configure(text=f"\u25bc  {self._title}")
        self._is_expanded = not self._is_expanded
