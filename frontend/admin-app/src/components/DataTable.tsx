import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type ColumnDef,
  type RowSelectionState,
  type OnChangeFn,
} from "@tanstack/react-table";
import {
  Checkbox,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TablePagination,
  TableRow,
  TableSortLabel,
} from "@mui/material";

import { EmptyState } from "@/components/ErrorState";

interface DataTableProps<T> {
  columns: ColumnDef<T, unknown>[];
  data: T[];
  total: number;
  page: number;
  pageSize: number;
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: number) => void;
  sort?: string;
  order?: "asc" | "desc";
  onSortChange?: (sort: string, order: "asc" | "desc") => void;
  getRowId?: (row: T) => string;
  rowSelection?: RowSelectionState;
  onRowSelectionChange?: OnChangeFn<RowSelectionState>;
  emptyTitle?: string;
  emptyDescription?: string;
  selectable?: boolean;
}

export function DataTable<T>({
  columns,
  data,
  total,
  page,
  pageSize,
  onPageChange,
  onPageSizeChange,
  sort,
  order = "asc",
  onSortChange,
  getRowId,
  rowSelection,
  onRowSelectionChange,
  emptyTitle = "No results",
  emptyDescription = "Try adjusting filters or create a new record.",
  selectable = false,
}: DataTableProps<T>) {
  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getRowId,
    enableRowSelection: selectable,
    state: { rowSelection: rowSelection ?? {} },
    onRowSelectionChange,
    manualPagination: true,
    manualSorting: true,
    pageCount: Math.max(1, Math.ceil(total / pageSize)),
  });

  if (!data.length) {
    return <EmptyState title={emptyTitle} description={emptyDescription} />;
  }

  return (
    <Paper variant="outlined" sx={{ overflow: "hidden" }}>
      <TableContainer>
        <Table size="small" aria-label="Data table">
          <TableHead>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {selectable ? (
                  <TableCell padding="checkbox">
                    <Checkbox
                      indeterminate={table.getIsSomeRowsSelected()}
                      checked={table.getIsAllPageRowsSelected()}
                      onChange={table.getToggleAllPageRowsSelectedHandler()}
                      inputProps={{ "aria-label": "Select all rows" }}
                    />
                  </TableCell>
                ) : null}
                {headerGroup.headers.map((header) => {
                  const canSort = Boolean(header.column.columnDef.enableSorting);
                  const id = header.column.id;
                  const active = sort === id;
                  return (
                    <TableCell key={header.id} sortDirection={active ? order : false}>
                      {header.isPlaceholder ? null : canSort && onSortChange ? (
                        <TableSortLabel
                          active={active}
                          direction={active ? order : "asc"}
                          onClick={() => {
                            const nextOrder =
                              active && order === "asc" ? "desc" : "asc";
                            onSortChange(id, nextOrder);
                          }}
                        >
                          {flexRender(
                            header.column.columnDef.header,
                            header.getContext(),
                          )}
                        </TableSortLabel>
                      ) : (
                        flexRender(
                          header.column.columnDef.header,
                          header.getContext(),
                        )
                      )}
                    </TableCell>
                  );
                })}
              </TableRow>
            ))}
          </TableHead>
          <TableBody>
            {table.getRowModel().rows.map((row) => (
              <TableRow key={row.id} selected={row.getIsSelected()} hover>
                {selectable ? (
                  <TableCell padding="checkbox">
                    <Checkbox
                      checked={row.getIsSelected()}
                      onChange={row.getToggleSelectedHandler()}
                      inputProps={{ "aria-label": `Select row ${row.id}` }}
                    />
                  </TableCell>
                ) : null}
                {row.getVisibleCells().map((cell) => (
                  <TableCell key={cell.id}>
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
      <TablePagination
        component="div"
        count={total}
        page={page - 1}
        onPageChange={(_, next) => onPageChange(next + 1)}
        rowsPerPage={pageSize}
        onRowsPerPageChange={(event) => {
          onPageSizeChange(Number(event.target.value));
          onPageChange(1);
        }}
        rowsPerPageOptions={[10, 25, 50]}
      />
    </Paper>
  );
}
