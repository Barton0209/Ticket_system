/** Колонки заявки — как в config.py / Tkinter */
export const ALL_COLUMNS = [
  "№",
  "Подразделение",
  "Отдел",
  "Операция",
  "Классификация",
  "Дата заказа",
  "Организация",
  "Ф.И.О.",
  "Ф.И.О лат",
  "Табельный номер",
  "Гражданство",
  "Дата рождения",
  "Вид документа",
  "Серия",
  "Номер",
  "Дата выдачи",
  "Дата окончания",
  "Кем выдан",
  "Адрес",
  "Маршрут",
  "Обоснование",
  "ПС",
  "АВИА/ЖД",
  "Дата вылета",
  "Примечание",
  "Ответственный",
  "Дата выписки",
  "Билет",
  "Сумма",
  "Оплата",
  "Причина возврата",
  "Последний перелет",
  "Телефон",
  "Трансфер",
];

/** Колонки базы: слева закреплены, Ф.И.О. широкая */
export const BASE_PINNED_COLUMNS = [
  "№",
  "Подразделение",
  "Отдел",
  "Ф.И.О.",
  "Табельный номер",
];

const BASE_COLUMN_WIDTHS = {
  "№": 52,
  Подразделение: 150,
  Отдел: 110,
  "Ф.И.О.": 280,
  "Ф.И.О лат": 200,
  "Табельный номер": 115,
  Гражданство: 100,
  "Дата рождения": 110,
  "Вид документа": 160,
  Серия: 70,
  Номер: 90,
  "Дата выдачи": 110,
  "Дата окончания": 115,
  "Кем выдан": 180,
  Адрес: 200,
  Телефон: 120,
};

export function buildBaseColumnDefs() {
  const pinned = new Set(BASE_PINNED_COLUMNS);
  const order = [
    ...BASE_PINNED_COLUMNS,
    ...ALL_COLUMNS.filter((c) => !pinned.has(c)),
  ];
  return order.map((col) => ({
    field: col,
    headerName: col,
    width: BASE_COLUMN_WIDTHS[col] ?? (col.length > 12 ? 115 : 90),
    minWidth: col === "Ф.И.О." ? 220 : 64,
    pinned: pinned.has(col) ? "left" : undefined,
    suppressSizeToFit: true,
    tooltipField: col,
  }));
}

export function emptyApplicationRow(index = 1, department = "") {
  const row = Object.fromEntries(ALL_COLUMNS.map((c) => [c, ""]));
  row["№"] = String(index);
  row["Подразделение"] = department;
  row["Операция"] = "Заказ";
  row["АВИА/ЖД"] = "АВИА";
  row["Оплата"] = "Монтаж";
  const d = new Date();
  row["Дата заказа"] = `${String(d.getDate()).padStart(2, "0")}.${String(d.getMonth() + 1).padStart(2, "0")}.${d.getFullYear()}`;
  return row;
}
