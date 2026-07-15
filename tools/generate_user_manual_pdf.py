from __future__ import annotations

import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "DoomsdayBot_Инструкция.pdf"
PORTABLE_OUTPUT = ROOT / "dist" / "DoomsdayBotPortable" / OUTPUT.name
ARCHIVE_BASE = ROOT / "dist" / "DoomsdayBotPortable"

PAGE_SIZE = (1240, 1754)
MARGIN_X = 92
TOP = 88
BOTTOM = 92

BG = "#F4F0E7"
INK = "#152128"
MUTED = "#5D686D"
ACCENT = "#E45B2B"
ACCENT_DARK = "#A83B18"
PANEL = "#FFFFFF"
SOFT = "#E8E2D7"
GREEN = "#2F725D"

FONT_REGULAR = Path(r"C:\Windows\Fonts\arial.ttf")
FONT_BOLD = Path(r"C:\Windows\Fonts\arialbd.ttf")


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_BOLD if bold else FONT_REGULAR), size)


F_COVER = font(76, True)
F_COVER_SUB = font(39, True)
F_SECTION = font(27, True)
F_TITLE = font(49, True)
F_H2 = font(31, True)
F_BODY = font(27)
F_BODY_BOLD = font(27, True)
F_SMALL = font(22)
F_FOOTER = font(19)


def text_width(draw: ImageDraw.ImageDraw, value: str, selected_font: ImageFont.FreeTypeFont) -> int:
    box = draw.textbbox((0, 0), value, font=selected_font)
    return box[2] - box[0]


def wrap_text(
    draw: ImageDraw.ImageDraw,
    value: str,
    selected_font: ImageFont.FreeTypeFont,
    max_width: int,
) -> list[str]:
    lines: list[str] = []
    for paragraph in value.split("\n"):
        if not paragraph:
            lines.append("")
            continue
        words = paragraph.split()
        current = words[0]
        for word in words[1:]:
            candidate = f"{current} {word}"
            if text_width(draw, candidate, selected_font) <= max_width:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)
    return lines


class Page:
    def __init__(self, section: str, title: str, page_number: int):
        self.image = Image.new("RGB", PAGE_SIZE, BG)
        self.draw = ImageDraw.Draw(self.image)
        self.y = TOP
        self.page_number = page_number
        self._header(section, title)

    def _header(self, section: str, title: str) -> None:
        self.draw.rounded_rectangle(
            (MARGIN_X, self.y, MARGIN_X + 90, self.y + 48),
            radius=16,
            fill=ACCENT,
        )
        self.draw.text((MARGIN_X + 20, self.y + 8), section, font=F_SECTION, fill="white")
        self.y += 76
        for line in wrap_text(self.draw, title, F_TITLE, PAGE_SIZE[0] - 2 * MARGIN_X):
            self.draw.text((MARGIN_X, self.y), line, font=F_TITLE, fill=INK)
            self.y += 62
        self.y += 20
        self.draw.line((MARGIN_X, self.y, PAGE_SIZE[0] - MARGIN_X, self.y), fill=ACCENT, width=4)
        self.y += 35

    def h2(self, value: str) -> None:
        self.y += 12
        self.draw.text((MARGIN_X, self.y), value, font=F_H2, fill=ACCENT_DARK)
        self.y += 47

    def paragraph(self, value: str, *, bold: bool = False, color: str = INK, gap: int = 18) -> None:
        selected_font = F_BODY_BOLD if bold else F_BODY
        for line in wrap_text(self.draw, value, selected_font, PAGE_SIZE[0] - 2 * MARGIN_X):
            self.draw.text((MARGIN_X, self.y), line, font=selected_font, fill=color)
            self.y += 40
        self.y += gap

    def bullets(self, values: list[str], *, numbered: bool = False) -> None:
        content_x = MARGIN_X + 54
        max_width = PAGE_SIZE[0] - MARGIN_X - content_x
        for index, value in enumerate(values, start=1):
            marker = f"{index}." if numbered else "•"
            self.draw.text((MARGIN_X + 6, self.y), marker, font=F_BODY_BOLD, fill=ACCENT)
            lines = wrap_text(self.draw, value, F_BODY, max_width)
            for line in lines:
                self.draw.text((content_x, self.y), line, font=F_BODY, fill=INK)
                self.y += 40
            self.y += 14
        self.y += 4

    def callout(self, title: str, value: str, *, color: str = GREEN) -> None:
        lines = wrap_text(self.draw, value, F_BODY, PAGE_SIZE[0] - 2 * MARGIN_X - 54)
        height = 70 + len(lines) * 40
        self.draw.rounded_rectangle(
            (MARGIN_X, self.y, PAGE_SIZE[0] - MARGIN_X, self.y + height),
            radius=22,
            fill=PANEL,
            outline=SOFT,
            width=2,
        )
        self.draw.rectangle((MARGIN_X, self.y, MARGIN_X + 12, self.y + height), fill=color)
        self.draw.text((MARGIN_X + 34, self.y + 22), title, font=F_BODY_BOLD, fill=color)
        line_y = self.y + 66
        for line in lines:
            self.draw.text((MARGIN_X + 34, line_y), line, font=F_BODY, fill=INK)
            line_y += 40
        self.y += height + 24

    def finish(self) -> Image.Image:
        if self.y > PAGE_SIZE[1] - BOTTOM - 38:
            raise RuntimeError(f"Page {self.page_number} content overflow: y={self.y}")
        footer_y = PAGE_SIZE[1] - 66
        self.draw.line((MARGIN_X, footer_y - 18, PAGE_SIZE[0] - MARGIN_X, footer_y - 18), fill=SOFT, width=2)
        self.draw.text((MARGIN_X, footer_y), "DOOMSDAY BOT • Руководство пользователя", font=F_FOOTER, fill=MUTED)
        page_text = str(self.page_number)
        self.draw.text(
            (PAGE_SIZE[0] - MARGIN_X - text_width(self.draw, page_text, F_FOOTER), footer_y),
            page_text,
            font=F_FOOTER,
            fill=MUTED,
        )
        return self.image


def cover() -> Image.Image:
    image = Image.new("RGB", PAGE_SIZE, INK)
    draw = ImageDraw.Draw(image)
    draw.ellipse((800, -160, 1420, 460), fill=ACCENT)
    draw.ellipse((-220, 1270, 430, 1920), outline="#34464E", width=36)
    draw.rounded_rectangle((MARGIN_X, 180, MARGIN_X + 180, 230), radius=18, fill=ACCENT)
    draw.text((MARGIN_X + 24, 190), "WINDOWS", font=F_SECTION, fill="white")
    y = 350
    draw.text((MARGIN_X, y), "DOOMSDAY", font=F_COVER, fill="white")
    y += 92
    draw.text((MARGIN_X, y), "BOT", font=F_COVER, fill=ACCENT)
    y += 160
    draw.text((MARGIN_X, y), "Руководство", font=F_COVER_SUB, fill="white")
    y += 55
    draw.text((MARGIN_X, y), "пользователя", font=F_COVER_SUB, fill="white")
    y += 120
    subtitle = "Portable-версия 2.1, обучение, рутинные задачи, группы и диагностика"
    for line in wrap_text(draw, subtitle, F_BODY, 820):
        draw.text((MARGIN_X, y), line, font=F_BODY, fill="#C8D2D6")
        y += 43
    draw.rounded_rectangle((MARGIN_X, 1305, PAGE_SIZE[0] - MARGIN_X, 1500), radius=26, fill="#223139")
    draw.text((MARGIN_X + 32, 1342), "Главное правило portable-версии", font=F_BODY_BOLD, fill=ACCENT)
    warning = "Запускайте EXE только из полной папки DoomsdayBotPortable. Папка _internal должна находиться рядом."
    line_y = 1390
    for line in wrap_text(draw, warning, F_BODY, PAGE_SIZE[0] - 2 * MARGIN_X - 64):
        draw.text((MARGIN_X + 32, line_y), line, font=F_BODY, fill="white")
        line_y += 40
    draw.text((MARGIN_X, PAGE_SIZE[1] - 100), "Версия руководства: 14.07.2026", font=F_SMALL, fill="#8FA0A8")
    return image


def build_pages() -> list[Image.Image]:
    pages = [cover()]

    page = Page("01", "Установка и быстрый запуск", 2)
    page.callout(
        "Правильный файл",
        "Используйте dist\\DoomsdayBotPortable\\DoomsdayBotPortable.exe или распакуйте DoomsdayBotPortable.zip целиком.",
    )
    page.h2("Установка")
    page.bullets(
        [
            "Распакуйте ZIP в отдельную папку, например C:\\DoomsdayBotPortable.",
            "Не запускайте программу прямо из архива и не используйте EXE из папки build.",
            "Не переносите один EXE отдельно: рядом обязательно должна оставаться папка _internal.",
            "Запустите DoomsdayBotPortable.exe двойным щелчком. Консольное окно появляться не должно.",
        ],
        numbered=True,
    )
    page.h2("Первый быстрый сценарий")
    page.bullets(
        [
            "Выберите рабочую область: весь экран, нужный монитор или выделенная область.",
            "Добавьте хотя бы один шаблон через кнопку «Выбрать область».",
            "Нажмите «Тест поиска» и убедитесь, что шаблон найден.",
            "Для обычного режима нажмите «Старт», для обученных игровых сценариев — зелёную кнопку «Старт рутины».",
        ],
        numbered=True,
    )
    pages.append(page.finish())

    page = Page("02", "Главное окно и рабочая область", 3)
    page.h2("Что показывает главное окно")
    page.bullets(
        [
            "Статус: остановлен, работает или находится на паузе.",
            "Счётчики областей, кликов и фактического времени работы без пауз.",
            "Строка состояния: что бот сейчас сканирует, что нашёл и почему мог отклонить совпадение.",
            "Мониторинг CPU, RAM и GPU, если дополнительные библиотеки доступны.",
        ]
    )
    page.h2("Рабочее поле")
    page.bullets(
        [
            "«Весь экран» подходит для одного монитора и стабильного расположения игры.",
            "«Монитор 1/2/…» ограничивает поиск конкретным экраном.",
            "«Выбранная область» ускоряет поиск и снижает ложные совпадения. Нажмите «Выбрать» и обведите игровое окно.",
        ]
    )
    page.callout(
        "Совет",
        "Чем меньше рабочая область, тем быстрее анализ. Оставьте небольшой запас вокруг элементов, которые могут смещаться.",
    )
    page.h2("Основные кнопки")
    page.paragraph("«Старт» запускает цикл, «Пауза» временно прекращает анализ, «Стоп» завершает работу, «Тест поиска» проверяет все активные шаблоны без запуска цикла.")
    pages.append(page.finish())

    page = Page("03", "Создание и редактирование шаблонов", 4)
    page.h2("Как добавить шаблон")
    page.bullets(
        [
            "Остановите бота и откройте нужный экран игры или программы.",
            "Нажмите «Выбрать область», зажмите левую кнопку мыши и обведите кнопку, надпись или значок.",
            "Введите понятное описание. При необходимости укажите группу — новую группу можно написать вручную.",
            "Сохраните область. PNG-файл и запись в config.json создаются автоматически.",
        ],
        numbered=True,
    )
    page.callout(
        "Хороший шаблон",
        "Выделяйте уникальный и стабильный фрагмент. Не захватывайте мигающую анимацию, таймеры и большие однотонные поля.",
    )
    page.h2("Управление областями")
    page.bullets(
        [
            "«Редактировать»: название, действие, задержка, точность, grayscale, группа и масштабирование.",
            "«Переснять область»: заменить изображение, сохранив настройки шаблона.",
            "«Вкл/Выкл»: временно исключить шаблон из поиска.",
            "«Вверх/Вниз» и перетаскивание: изменить приоритет проверки.",
            "«Копировать в группу»: создать независимую копию шаблона для другого сценария.",
            "«Удалить»: удалить запись и связанный PNG-файл с диска.",
        ]
    )
    pages.append(page.finish())

    page = Page("04", "Точность, масштаб и действия", 5)
    page.h2("Точность поиска")
    page.bullets(
        [
            "Начните с 0,88–0,92. Повышайте значение при ложных совпадениях, снижайте понемногу, если правильный элемент не находится.",
            "Grayscale сравнивает форму без строгой привязки к цвету. Отключите его, если цвет является важным отличием.",
            "Масштабирование помогает при изменении DPI, размера окна или разрешения. Используйте небольшой диапазон, чтобы не замедлять поиск.",
            "ORB проверяет ключевые точки на сложных изображениях. На маленьких текстовых кнопках он может не дать преимущества.",
            "Защита от зацикливания временно блокирует повторный клик по тем же координатам.",
        ]
    )
    page.h2("Действия шаблона")
    page.bullets(
        [
            "click — обычный клик; double_click — двойной; right_click — правой кнопкой.",
            "«Числа для ввода» позволяют после клика напечатать заданные значения.",
            "«Последовательность кликов» выполняет дополнительные клики со смещениями dx,dy.",
            "«Задержка» задаёт паузу после успешного действия; «Кулдаун» защищает шаблон от слишком частого повторения.",
        ]
    )
    page.callout(
        "Настройка без риска",
        "После любого изменения сначала используйте «Тест поиска». Запускайте автоматический цикл только после проверки координат и точности.",
        color=ACCENT,
    )
    pages.append(page.finish())

    page = Page("05", "Рутинные задачи: одна кнопка запуска", 6)
    page.h2("Что делает диспетчер")
    page.bullets(
        [
            "Сначала проверяет лечение: забирает готовых бойцов и снова запускает лечение.",
            "Затем чередует еду, дерево, металл и нефть, пока не будут заняты пять походов.",
            "«Охота за призом» включается отдельной галочкой во время события и имеет приоритет над обычным сбором.",
            "После каждого клика бот заново анализирует экран, поэтому меняющиеся кнопки обрабатываются как последовательность шагов.",
        ]
    )
    page.h2("Однократное обучение")
    page.bullets(
        [
            "Откройте «Настроить задачи», выберите задачу и нажмите «Снять шаблон».",
            "По очереди сохраните устойчивые кнопки сценария в одну группу.",
            "Для походной задачи укажите финальный шаблон кнопки «Отправить» и примерную длительность похода.",
            "После проверки оставьте включёнными нужные задачи и нажмите «Старт рутины».",
        ],
        numbered=True,
    )
    page.callout(
        "Перенос на другой ПК",
        "В окне настройки нажмите «Экспорт обучения». На другом ПК используйте «Импорт обучения». Лучше установить одинаковое разрешение LDPlayer, например 1280×720 и 240 DPI.",
    )
    pages.append(page.finish())

    page = Page("06", "Группы, расписание и циклы", 7)
    page.h2("Группы")
    page.paragraph("Группа объединяет связанные шаблоны. Галочка группы на главном экране сразу включает или выключает все её активные области.")
    page.bullets(
        [
            "Создайте группу при сохранении шаблона или укажите её в редакторе.",
            "Используйте отдельные группы для аккаунтов, режимов игры или разных окон.",
            "Переименование группы обновляет её шаблоны, расписание и циклические профили.",
        ]
    )
    page.h2("Расписание групп")
    page.paragraph("В «Расписание групп» включите «Авто» и задайте время включения/выключения в формате ЧЧ:ММ. Вместо времени выключения можно использовать длительность в минутах.")
    page.h2("Порядок и циклы аккаунтов")
    page.bullets(
        [
            "На вкладке порядка расположите группы в нужной последовательности и задайте задержки.",
            "В циклическом режиме добавьте группы в список и установите таймаут бездействия.",
            "Если в текущей группе нет действий дольше таймаута, бот переключится на следующую.",
            "Профили циклов позволяют хранить несколько независимых наборов групп и быстро переключаться между ними.",
        ]
    )
    pages.append(page.finish())

    page = Page("07", "Безопасная работа и диагностика", 8)
    page.h2("Рекомендуемый порядок")
    page.bullets(
        [
            "Подготовьте окно программы и не меняйте его масштаб во время работы.",
            "Остановите или поставьте бота на паузу перед редактированием областей.",
            "Проверьте активные группы и рабочую область.",
            "Запустите «Тест поиска» и прочитайте итог в строке состояния.",
            "После успешного теста нажмите «Старт» и первые минуты наблюдайте за действиями.",
        ],
        numbered=True,
    )
    page.h2("Горячие клавиши")
    page.bullets(
        [
            "Ctrl+P — поставить на паузу или продолжить.",
            "Ctrl+0 — аварийная остановка.",
            "Enter — подтвердить диалог; Esc — отменить; Delete — удалить выбранное.",
            "Пробел — включить/выключить область; Ctrl+↑/↓ — изменить порядок.",
        ]
    )
    page.callout(
        "Аварийная остановка",
        "Если курсор ведёт себя неожиданно, сразу нажмите Ctrl+0. После остановки проверьте строку состояния, рабочую область и точность шаблона.",
        color=ACCENT,
    )
    pages.append(page.finish())

    page = Page("08", "Данные, обновление и устранение ошибок", 9)
    page.h2("Что нужно сохранять")
    page.bullets(
        [
            "config.json — настройки, группы, расписания и список шаблонов.",
            "img — изображения всех областей и подпапки групп.",
            "backups\\config — автоматические резервные копии конфигурации.",
            "ZIP-профиль обучения — перенос рутинных сценариев и их шаблонов между ПК.",
            "bot.log — журнал для диагностики; его можно удалить при закрытой программе, если он стал слишком большим.",
        ]
    )
    page.h2("Обновление portable-версии")
    page.paragraph("Закройте программу, сохраните копии config.json и img, затем распакуйте новую portable-папку. Не заменяйте только один EXE и не удаляйте _internal.")
    page.h2("Частые проблемы")
    page.bullets(
        [
            "Failed to load Python DLL: запущен EXE из build или EXE перенесён без _internal. Запускайте файл из полной папки dist\\DoomsdayBotPortable.",
            "Шаблон не находится: проверьте рабочую область, запустите тест, переснимите шаблон и попробуйте точность 0,88–0,92.",
            "Ложные клики: увеличьте точность, сузьте рабочую область, включите проверку цвета/ORB и защиту от зацикливания.",
            "Редактирование недоступно: остановите бота или поставьте его на паузу.",
            "Программа закрывается: откройте bot.log в portable-папке и проверьте последние строки.",
        ]
    )
    pages.append(page.finish())

    return pages


def main() -> None:
    pages = build_pages()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    pages[0].save(
        OUTPUT,
        "PDF",
        resolution=150.0,
        save_all=True,
        append_images=pages[1:],
    )

    if ARCHIVE_BASE.exists():
        shutil.copy2(OUTPUT, PORTABLE_OUTPUT)


if __name__ == "__main__":
    main()
