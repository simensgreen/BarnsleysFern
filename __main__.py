import tkinter as tk
import tkinter.ttk as ttk
import typing
from functools import lru_cache
from random import random
from tkinter.colorchooser import askcolor
from tkinter.filedialog import asksaveasfilename

import glm
from PIL import Image, ImageTk, ImageDraw


__author__ = 'simens_green'
__version__ = '1.0.0'

# Имена доступных секций
# Available section names
SECTIONS = 'first', 'second', 'third', 'fourth'

# Стандандартные значения всех параметров
# Standard values of all parameters
DEFAULTS = {
    'first': {'form': glm.mat2(0, 0, 0, .16), 'offset': glm.vec2(0, 0), 'probability': .01},
    'second': {'form': glm.mat2(.85, .04, -.04, .85), 'offset': glm.vec2(0, 1.6), 'probability': .86},
    'third': {'form': glm.mat2(-0.2, .26, .23, .4), 'offset': glm.vec2(0, 1.6), 'probability': .93},
    'fourth': {'form': glm.mat2(-.15, .28, .26, .24), 'offset': glm.vec2(0, .44), 'probability': 0},
    'number of points': 10 ** 5
}

# Диапазоны для шкал (в этих диапазонах картинка выглядит прилично,
# но пользователь в поле ввода может установить произвольное)
# Ranges for scales (in these ranges the picture looks decent,
# but the user can set arbitrary in the input field)
SCALE_RANGES = {
    'first': {'form': (((-.5, .5), (-.5, .5)), ((-.07, .045), (-.5, .5))),
              'offset': ((-1, 1), (-5, 5)), 'probability': (0, 1)},

    'second': {'form': (((.45, 1), (-.5, 1.5)), ((-.3, .2), (.3, .95))),
               'offset': ((-3, 1), (.2, 4)), 'probability': (0, 1)},

    'third': {'form': (((-.5, .5), (-2, 2)), ((-1.5, 2), (-.28, .9))),
              'offset': ((-5, 5), (-4, 4)), 'probability': (0, 1)},

    'fourth': {'form': (((-.8, .7), (-1, 2)), ((-1.5, 1.5), (-.5, .8))),
               'offset': ((-5, 5), (-7, 9)), 'probability': (0, 1)},

    'number of points': (0, 2 * 10 ** 5)
}


@lru_cache(maxsize=1024)
def __transform(form: glm.mat2, current_point: glm.vec2, offset: glm.vec2) -> glm.vec2:
    return form * current_point + offset


def fern_point_generator(number_of_points: int, options: dict):
    """
    Генерирует значения точек-пикселей папоротника

    Generates fern pixel point values

    Args:
        number_of_points (int): количество точек
        options (dict): собственные опции для точек, вместо стандартных
                 own options for points instead of standard

    Yields:
        glm.vec2: точка. A point
    """
    current_point = glm.vec2(0, 0)

    for point_no in range(number_of_points):
        value = random()

        if value < options['first']['probability']:
            current_point = __transform(options['first']['form'], current_point, options['first']['offset'])
        elif value < options['second']['probability']:
            current_point = __transform(options['second']['form'], current_point, options['second']['offset'])
        elif value < options['third']['probability']:
            current_point = __transform(options['third']['form'], current_point, options['third']['offset'])
        else:
            current_point = __transform(options['fourth']['form'], -current_point, options['fourth']['offset'])

        yield current_point


def rescale_points(points: typing.Iterable, image_size: typing.Tuple[int, int]):
    """
    Масштабирует точки (иначе размер папоротника очень мал и вверх ногами)

    Scales points (otherwise the fern size is very small and upside down)

    Args:
        points (typing.Iterable[glm.vec2]): Набор точек. Iterable of points.
        image_size (typing.Tuple[int, int]): Размер итогового изображения. Final image size

    Yields:
        glm.vec2: Scaled point
    """
    factor = min(image_size) / 10.5
    for point in points:
        point = point * factor
        yield int(point[0] + image_size[0] / 2), int(point[1])


def create_scale_and_entry_pair(root, var: tk.Variable,
                                scale_range: typing.Tuple[float, float],
                                state='normal') -> tk.Frame:
    """
    Создает пару: шкала - текстовое поле

    Creates a pair: Scale - Entry

    Args:
        root: родительский виджет для будущей пары. root widget for pair
        var (tk.Variable): переменная, с которой будет синхронизирована шкала и текстовое поле. the variable with which
        the scale and text box will be synchronized
        scale_range (typing.Tuple[float, float]): диапазон значений шкалы.
        state (str): состояние шкалы и текстового поля.

    Returns:
        tk.Frame: готовая пара.
    """
    frame = tk.Frame(root)

    scale = ttk.Scale(frame, variable=var, from_=scale_range[0], to=scale_range[1])
    scale['state'] = state
    scale.pack(side=tk.LEFT)

    entry = ttk.Entry(frame, textvar=var, width=8)
    entry['state'] = state
    entry.pack(side=tk.RIGHT)

    return frame


def rgb_byte_to_hex(color: typing.Tuple[int, ...]):
    """
    Конвертирует RGB цвет в байтах (0..256) в HTML Hex

    Converts RGB color in bytes (0..256) to HTML Hex

    Args:
        color (typing.Tuple[int, ...]): цвет RGB. RGB color

    Returns:
        str: HTML Hex
    """
    return '#%.2x%.2x%.2x' % (color[0], color[1], color[2])


class App:
    size = 720, 1024  # примерный размер окна в пикселях. approximate window size in pixels

    main_color = (0, 255, 0)  # цвет рисунка. picture color
    canvas_bg = (0, 0, 0)  # цвет холста. canvas color

    tk_vars = {}

    image = None
    tk_image = None

    allow_update = False

    def __init__(self):
        self.root = tk.Tk()
        self.root.title('Barnsley\'s Fern')

        self.__load_tk_vars()

        self.canvas = tk.Canvas(self.root, width=self.size[0], height=self.size[0], bg=rgb_byte_to_hex(self.canvas_bg))
        self.canvas.grid(row=0, column=0, rowspan=2)

        self.main_controls = tk.Frame(self.root)
        self.main_controls.grid(row=0, column=1)
        self.__load_main_controls()

        self.additional_control = tk.Frame(self.root)
        self.additional_control.grid(row=1, column=1)
        self.__load_additional_controls()

        self.__load_image()
        self.update()

    def __load_tk_vars(self):
        self.tk_vars = {
            section: {
                'form': [
                    [self.__gen_tk_var(DEFAULTS[section]['form'][0][0]),
                     self.__gen_tk_var(DEFAULTS[section]['form'][0][1])],
                    [self.__gen_tk_var(DEFAULTS[section]['form'][1][0]),
                     self.__gen_tk_var(DEFAULTS[section]['form'][1][1])],
                ],
                'offset': [self.__gen_tk_var(DEFAULTS[section]['offset'][0]),
                           self.__gen_tk_var(DEFAULTS[section]['offset'][1])],
                'probability': self.__gen_tk_var(DEFAULTS[section]['probability'])
            }
            for section in SECTIONS
        }
        self.tk_vars['number of points'] = self.__gen_tk_var(DEFAULTS['number of points'])
        self.allow_update = True

    def __load_additional_controls(self):
        num_of_points_frame = tk.Frame(self.additional_control)
        num_of_points_frame.pack()
        tk.Label(num_of_points_frame, text='Количество точек:', font=('Arial', 14)).pack(side=tk.LEFT, padx=5)
        ttk.Scale(num_of_points_frame, len_=self.size[0] / 2, variable=self.tk_vars['number of points'],
                  from_=SCALE_RANGES['number of points'][0],
                  to=SCALE_RANGES['number of points'][1]).pack(side=tk.LEFT)
        ttk.Entry(num_of_points_frame, textvar=self.tk_vars['number of points']).pack(side=tk.LEFT)

        buttons_frame = tk.Frame(self.additional_control)
        buttons_frame.pack()

        ttk.Button(buttons_frame, text='Обновить',
                   command=self.update).pack(side=tk.LEFT)
        ttk.Button(buttons_frame, text='Восстановить стандартные значения',
                   command=self.set_defaults).pack(side=tk.LEFT)
        ttk.Button(buttons_frame, text='Цвет заднего фона',
                   command=self.change_bg).pack(side=tk.LEFT)
        ttk.Button(buttons_frame, text='Цвет рисунка',
                   command=self.change_fg).pack(side=tk.LEFT)
        ttk.Button(buttons_frame, text='Сохранить изображение',
                   command=self.save_image).pack(side=tk.LEFT)

    def __gen_tk_var(self, value: float = None):
        var = tk.DoubleVar()
        if value is not None:
            var.set(value)
        var.trace_add('write', self.update)
        return var

    def __form_controls(self, root, section):
        frame = tk.Frame(root)
        for i in range(2):
            for j in range(2):
                create_scale_and_entry_pair(frame, self.tk_vars[section]['form'][i][j],
                                            SCALE_RANGES[section]['form'][i][j]).grid(row=i, column=j)
        return frame

    def __offset_controls(self, root, section):
        frame = tk.Frame(root)
        create_scale_and_entry_pair(frame, self.tk_vars[section]['offset'][0],
                                    SCALE_RANGES[section]['offset'][0]).pack(side=tk.LEFT)
        create_scale_and_entry_pair(frame, self.tk_vars[section]['offset'][1],
                                    SCALE_RANGES[section]['offset'][1]).pack(side=tk.RIGHT)
        return frame

    def __probability_controls(self, root, section):
        return create_scale_and_entry_pair(root, self.tk_vars[section]['probability'],
                                           SCALE_RANGES[section]['probability'],
                                           state='normal' if section != 'fourth' else 'disabled')

    def __section_controls(self, root, section):
        frame = tk.Frame(root)
        self.__form_controls(frame, section).pack(pady=10)
        self.__offset_controls(frame, section).pack(pady=10)
        self.__probability_controls(frame, section).pack(pady=10)
        return frame

    def __load_main_controls(self):
        for no, section in enumerate(SECTIONS):
            self.__section_controls(self.main_controls, section).grid(row=no // 2, column=no % 2, pady=20, padx=20)

    def __create_image(self):
        return Image.new('RGBA', (self.size[0], self.size[0]), color=self.canvas_bg)

    def __load_image(self):
        self.image = self.__create_image()
        self.tk_image = ImageTk.PhotoImage(image=self.image)
        self.canvas.create_image(self.size[0] / 2 + 2, self.size[0] / 2 + 2, image=self.tk_image, tag=('image',))

    def get_values(self):
        values = {
            section: {
                'form': glm.mat2x2(self.tk_vars[section]['form'][0][0].get(), self.tk_vars[section]['form'][0][1].get(),
                                   self.tk_vars[section]['form'][1][0].get(), self.tk_vars[section]['form'][1][1].get()
                                   ),
                'offset': glm.vec2(self.tk_vars[section]['offset'][0].get(), self.tk_vars[section]['offset'][1].get()),
                'probability': self.tk_vars[section]['probability'].get()
            }
            for section in SECTIONS
        }
        return values

    def update(self, *args):
        if self.image and self.allow_update:
            self.canvas.delete('image')
            self.image = self.__create_image()
            draw = ImageDraw.Draw(self.image)
            draw.point(list(set(rescale_points(fern_point_generator(int(self.tk_vars['number of points'].get()),
                                                                    self.get_values()), self.image.size))),
                       fill=self.main_color)
            self.tk_image = ImageTk.PhotoImage(image=self.image.rotate(180))
            self.canvas.create_image(self.size[0] / 2 + 2, self.size[0] / 2 + 2, image=self.tk_image, tag=('image',))
        return args

    def change_bg(self):
        color = tuple(map(int, askcolor(rgb_byte_to_hex(self.canvas_bg))[0]))
        self.canvas_bg = color
        self.canvas['bg'] = rgb_byte_to_hex(color)
        self.update()

    def change_fg(self):
        color = tuple(map(int, askcolor(rgb_byte_to_hex(self.main_color))[0]))
        self.main_color = color
        self.update()

    def save_image(self):
        path = asksaveasfilename()
        self.image.rotate(180).save(path + '.png', format='PNG')

    def set_defaults(self):
        self.allow_update = False
        for section in SECTIONS:
            for i in range(2):
                for j in range(2):
                    self.tk_vars[section]['form'][i][j].set(DEFAULTS[section]['form'][i][j])
            self.tk_vars[section]['offset'][0].set(DEFAULTS[section]['offset'][0])
            self.tk_vars[section]['offset'][1].set(DEFAULTS[section]['offset'][1])
            self.tk_vars[section]['probability'].set(DEFAULTS[section]['probability'])
        self.tk_vars['number of points'].set(DEFAULTS['number of points'])
        self.allow_update = True
        self.update()

    def run(self):
        """
        Запуск приложения
        Run this application

        Returns:
            None
        """
        self.root.mainloop()


# Точка входа. Entry point
if __name__ == '__main__':
    app = App()
    app.run()
