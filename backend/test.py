from server import convert_moves_to_ttk

def assert_eq(item_1, item_2) -> None:
    if item_1 != item_2:
        print(f"{item_1} != {item_2}")
        exit()

if __name__ == "__main__":

    assert_eq(convert_moves_to_ttk("x2".split(), 7), ["x2"])
    assert_eq(convert_moves_to_ttk("R U R' U'".split(), 7), ["R", "U", "R'", "U'"])
    assert_eq(convert_moves_to_ttk("2Rw 5R".split(), 7), ["r", "3l'", "l"])
    assert_eq(convert_moves_to_ttk("3F 4Fw".split(), 7), ["3f", "f'", "3b", "z"])
    assert_eq(convert_moves_to_ttk("2U 5U".split(), 8), ["u", "U'", "4d'", "3d"])

    # testing middle layer moves
    assert_eq(convert_moves_to_ttk("4D".split(), 7), ["E"])
    assert_eq(convert_moves_to_ttk("4F".split(), 7), ["S'"])
    assert_eq(convert_moves_to_ttk("4R".split(), 7), ["M'"])
