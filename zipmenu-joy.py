#!/usr/bin/env python3
# Converte controle (joystick/gamepad) em teclas para o menu do zipmenu.
# D-pad / analogico esquerdo: cima/baixo/esquerda/direita | A: Enter | B: Esc | X: tecla x (abre Add/Remove) | LB/RB: PgUp/PgDn
import select
import time

from evdev import InputDevice, UInput, ecodes as e, list_devices

OUT_KEYS = [e.KEY_UP, e.KEY_DOWN, e.KEY_ENTER, e.KEY_ESC,
            e.KEY_PAGEUP, e.KEY_PAGEDOWN, e.KEY_LEFT, e.KEY_RIGHT, e.KEY_X]

BTN_ENTER = {e.BTN_SOUTH, e.BTN_START, e.BTN_TRIGGER}
BTN_ESC = {e.BTN_EAST, e.BTN_SELECT, e.BTN_THUMB}
BTN_X = {e.BTN_X, e.BTN_THUMB2}   # botao X (BTN_X = BTN_NORTH) / 3o botao de joystick generico
BTN_PGUP = {e.BTN_TL}
BTN_PGDN = {e.BTN_TR}

REPEAT_DELAY = 0.35
REPEAT_RATE = 0.10

BTN_DPAD_UP = getattr(e, "BTN_DPAD_UP", -1)
BTN_DPAD_DOWN = getattr(e, "BTN_DPAD_DOWN", -1)
BTN_DPAD_LEFT = getattr(e, "BTN_DPAD_LEFT", -1)
BTN_DPAD_RIGHT = getattr(e, "BTN_DPAD_RIGHT", -1)
HOLD_CLEAR_CODES = {BTN_DPAD_UP, BTN_DPAD_DOWN} | BTN_PGUP | BTN_PGDN


def is_pad(dev):
    caps = dev.capabilities()
    if e.EV_ABS not in caps:
        return False
    keys = caps.get(e.EV_KEY, [])
    return any(k in keys for k in (e.BTN_SOUTH, e.BTN_TRIGGER, e.BTN_JOYSTICK))


def main():
    pads = []
    for path in list_devices():
        try:
            d = InputDevice(path)
            if is_pad(d):
                pads.append(d)
        except Exception:
            pass
    if not pads:
        return

    ui = UInput({e.EV_KEY: OUT_KEYS}, name="zipmenu-joy")
    fds = {d.fd: d for d in pads}
    start = time.time()
    held = None          # tecla segurada (para repeticao)
    next_rep = 0.0
    axis_dir = {}        # estado do analogico por dispositivo
    axis_dirx = {}       # idem, eixo horizontal (esquerda/direita)

    def tap(key):
        ui.write(e.EV_KEY, key, 1)
        ui.write(e.EV_KEY, key, 0)
        ui.syn()

    try:
        while True:
            r, _, _ = select.select(list(fds), [], [], 0.05)
            now = time.time()
            for fd in r:
                dev = fds[fd]
                try:
                    events = list(dev.read())
                except OSError:
                    continue
                for ev in events:
                    if now - start < 0.4:
                        continue
                    new_held = None
                    if ev.type == e.EV_KEY and ev.value == 1:
                        if ev.code in BTN_ENTER:
                            tap(e.KEY_ENTER)
                        elif ev.code in BTN_ESC:
                            tap(e.KEY_ESC)
                        elif ev.code in BTN_X:
                            tap(e.KEY_X)
                        elif ev.code == BTN_DPAD_LEFT:
                            tap(e.KEY_LEFT)
                        elif ev.code == BTN_DPAD_RIGHT:
                            tap(e.KEY_RIGHT)
                        elif ev.code in BTN_PGUP:
                            new_held = e.KEY_PAGEUP
                        elif ev.code in BTN_PGDN:
                            new_held = e.KEY_PAGEDOWN
                        elif ev.code == BTN_DPAD_UP:
                            new_held = e.KEY_UP
                        elif ev.code == BTN_DPAD_DOWN:
                            new_held = e.KEY_DOWN
                        else:
                            continue
                        if new_held:
                            tap(new_held)
                            held = new_held
                            next_rep = now + REPEAT_DELAY
                    elif ev.type == e.EV_KEY and ev.value == 0:
                        if ev.code in HOLD_CLEAR_CODES:
                            held = None
                    elif ev.type == e.EV_ABS and ev.code in (e.ABS_HAT0X, e.ABS_X):
                        if ev.code == e.ABS_HAT0X:
                            direction = ev.value
                        else:
                            info = dev.absinfo(e.ABS_X)
                            mid = (info.max + info.min) / 2.0
                            span = (info.max - info.min) / 2.0 or 1.0
                            n = (ev.value - mid) / span
                            direction = -1 if n < -0.5 else (1 if n > 0.5 else 0)
                        key = e.KEY_LEFT if direction < 0 else (
                            e.KEY_RIGHT if direction > 0 else None)
                        if axis_dirx.get((fd, ev.code)) == key:
                            continue
                        axis_dirx[(fd, ev.code)] = key
                        if key:
                            tap(key)   # esquerda/direita: um toque por apertada (sem repeticao)
                    elif ev.type == e.EV_ABS and ev.code in (e.ABS_HAT0Y, e.ABS_Y):
                        if ev.code == e.ABS_HAT0Y:
                            direction = ev.value
                        else:
                            info = dev.absinfo(e.ABS_Y)
                            mid = (info.max + info.min) / 2.0
                            span = (info.max - info.min) / 2.0 or 1.0
                            n = (ev.value - mid) / span
                            direction = -1 if n < -0.5 else (1 if n > 0.5 else 0)
                        key = e.KEY_UP if direction < 0 else (
                            e.KEY_DOWN if direction > 0 else None)
                        if ev.code == e.ABS_Y and axis_dir.get(fd) == key:
                            continue
                        if ev.code == e.ABS_Y:
                            axis_dir[fd] = key
                        if key:
                            tap(key)
                            held = key
                            next_rep = now + REPEAT_DELAY
                        else:
                            held = None
            if held and now >= next_rep:
                tap(held)
                next_rep = now + REPEAT_RATE
    finally:
        ui.close()


if __name__ == "__main__":
    main()
