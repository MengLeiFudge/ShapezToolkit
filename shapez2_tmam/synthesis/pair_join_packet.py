"""为双半形的拼合与复位方向生成六槽指令。"""


def pair_join_word(kind: int, step: int, left: int, right: int) -> int:
    # 11/13 在右槽旋转，2x/3x 完成并写入指定目的槽。
    if kind == 2:
        if left < 0:
            if (step == 0) & (right >= 0):
                return 34
        elif right < 0:
            if step == 0:
                return 24
        elif step == 0:
            return 1
        elif step == 1:
            return 11
        elif step == 2:
            return 8
        elif step == 3:
            return 2
        elif step == 4:
            return 24
    if (kind == 3) & (right >= 0):
        if step == 0:
            if left < 0:
                return 33
            return 13
        if (step == 1) & (left >= 0):
            return 28
    if (kind == 5) & (step == 0) & (left >= 0):
        return 21
    return 0


def pair_join_opcode(word: int, left: int, right: int, destination: int) -> int:
    if (word == 11) | (word == 21):
        return 1
    if (word == 13) | (word == 33):
        return 3
    if (word == 24) | (word == 34):
        return 4
    if word == 28:
        return 8
    return word


def pair_join_a(word: int, left: int, right: int, destination: int) -> int:
    if (word == 11) | (word == 13) | (word == 33) | (word == 34):
        return right
    return left


def pair_join_b(word: int, left: int, right: int, destination: int) -> int:
    return right


def pair_join_destination(word: int, left: int, right: int, destination: int) -> int:
    if word >= 20:
        return destination
    return pair_join_a(word, left, right, destination)


def pair_join_active(word: int, left: int, right: int, destination: int) -> bool:
    return word != 0


def pair_join_two_inputs(word: int, left: int, right: int, destination: int) -> bool:
    return (word == 8) | (word == 28)
