"""ui/screen_manage_projects.py - Admin "Projects" (2026-11-16, both apps; web /admin/projects).

tblProject (number, name, process, description) - the projects offered in Create Experiment Request and Create
Experiment. Same table screen as Order Type (ui/screen_manage_order_types.py), logic in db/master_tables.py
(KINDS["projects"]): the column "UsedBy" (experiments + requests) is shown only, a project number may exist only
once, a project that is still used cannot be deleted."""
from PySide6.QtCore import Qt

from ui.screen_manage_order_types import ManageOrderTypeScreen, GenericEditableModel


class _ProjectModel(GenericEditableModel):
    """UsedBy is computed - never editable."""

    def flags(self, index):
        f = super().flags(index)
        if index.isValid() and self._headers[index.column()] == "UsedBy":
            return f & ~Qt.ItemIsEditable
        return f


class ManageProjectsScreen(ManageOrderTypeScreen):
    TABLE = 'tblProject'
    _SCREEN_KEY = 'manage_projects'
    _KIND = 'projects'

    def reload_data(self):
        super().reload_data()
        # swap in the model that keeps UsedBy read-only (same rows/headers)
        if self.model is not None and not isinstance(self.model, _ProjectModel):
            m = _ProjectModel(self.model.rows(), self.model.headers(), id_column=self.model.id_column(),
                              read_only=self._read_only)
            self.model = m
            self.proxy.setSourceModel(m)
            self._restore_column_order()
