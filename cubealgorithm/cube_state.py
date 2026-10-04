
class CubeState:
    """Cubie state: permutation and orientation for 8 corners and 12 edges."""

    def __init__(self, corner_permutation, corner_orientation, edge_permutation, edge_orientation):
        self.corner_permutation = corner_permutation.copy()
        self.corner_orientation = corner_orientation.copy()
        self.edge_permutation = edge_permutation.copy()
        self.edge_orientation = edge_orientation.copy()

    def __repr__(self):
        return (f"CubeState(corner_permutation={self.corner_permutation}, "
                f"corner_orientation={self.corner_orientation}, "
                f"edge_permutation={self.edge_permutation}, "
                f"edge_orientation={self.edge_orientation})")

    @classmethod
    def solved(cls):
        return cls(
            corner_permutation=[0, 1, 2, 3, 4, 5, 6, 7],
            corner_orientation=[0, 0, 0, 0, 0, 0, 0, 0],
            edge_permutation=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
            edge_orientation=[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        )

    def __eq__(self, other):
        return (self.corner_permutation == other.corner_permutation and
                self.corner_orientation == other.corner_orientation and
                self.edge_permutation == other.edge_permutation and
                self.edge_orientation == other.edge_orientation)

    _SOLVED_CORNER_PERM = (0, 1, 2, 3, 4, 5, 6, 7)
    _SOLVED_CORNER_ORI = (0, 0, 0, 0, 0, 0, 0, 0)
    _SOLVED_EDGE_PERM = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11)
    _SOLVED_EDGE_ORI = (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

    def is_solved(self):
        return (
            tuple(self.corner_permutation) == self._SOLVED_CORNER_PERM
            and tuple(self.corner_orientation) == self._SOLVED_CORNER_ORI
            and tuple(self.edge_permutation) == self._SOLVED_EDGE_PERM
            and tuple(self.edge_orientation) == self._SOLVED_EDGE_ORI
        )

    def permutation_parity(self, permutation):
        inversion_count = 0

        for first_index in range(len(permutation)):
            for second_index in range(first_index + 1, len(permutation)):
                if permutation[first_index] > permutation[second_index]:
                    inversion_count += 1

        return inversion_count % 2

    def is_valid(self):
        corner_parity = self.permutation_parity(self.corner_permutation)
        edge_parity = self.permutation_parity(self.edge_permutation)

        if corner_parity != edge_parity:
            return False
        if len(self.corner_orientation) != 8 or len(self.edge_orientation) != 12:
            return False
        if sorted(self.corner_permutation) != list(range(8)):
            return False
        if sorted(self.edge_permutation) != list(range(12)):
            return False
        if not all(num in [0, 1, 2] for num in self.corner_orientation):
            return False
        if not all(num in [0, 1] for num in self.edge_orientation):
            return False
        if sum(self.corner_orientation) % 3 != 0:
            return False
        if sum(self.edge_orientation) % 2 != 0:
            return False
        return True

    def move_u(self):
        corner_permutation = self.corner_permutation.copy()
        corner_orientation = self.corner_orientation.copy()
        edge_permutation = self.edge_permutation.copy()
        edge_orientation = self.edge_orientation.copy()

        corner_permutation.insert(0, corner_permutation.pop(3))
        edge_permutation.insert(0, edge_permutation.pop(3))

        corner_orientation.insert(0, corner_orientation.pop(3))
        edge_orientation.insert(0, edge_orientation.pop(3))

        return CubeState(
            corner_permutation,
            corner_orientation,
            edge_permutation,
            edge_orientation
        )

    def move_d(self):
        corner_permutation = self.corner_permutation.copy()
        corner_orientation = self.corner_orientation.copy()
        edge_permutation = self.edge_permutation.copy()
        edge_orientation = self.edge_orientation.copy()

        corner_permutation.insert(7, corner_permutation.pop(4))
        edge_permutation.insert(7, edge_permutation.pop(4))

        corner_orientation.insert(7, corner_orientation.pop(4))
        edge_orientation.insert(7, edge_orientation.pop(4))

        return CubeState(
            corner_permutation,
            corner_orientation,
            edge_permutation,
            edge_orientation
        )

    def move_f(self):
        corner_permutation = self.corner_permutation.copy()
        corner_orientation = self.corner_orientation.copy()
        edge_permutation = self.edge_permutation.copy()
        edge_orientation = self.edge_orientation.copy()

        corner_sources = [0, 1, 5, 4]
        corner_destinations = [4, 0, 1, 5]
        corner_changes = [2, 1, 2, 1]
        edge_sources = [1, 9, 5, 8]
        edge_destinations = [8, 1, 9, 5]
        for edge_destination, edge_source in zip(edge_destinations, edge_sources):
            edge_permutation[edge_destination] = self.edge_permutation[edge_source]
            edge_orientation[edge_destination] = (self.edge_orientation[edge_source] + 1) % 2

        
        for corner_destination, corner_source, corner_change in zip(corner_destinations, corner_sources, corner_changes):
            corner_permutation[corner_destination] = self.corner_permutation[corner_source]
            corner_orientation[corner_destination] = (self.corner_orientation[corner_source] + corner_change) % 3

        return CubeState(
            corner_permutation,
            corner_orientation,
            edge_permutation,
            edge_orientation
        )

    def move_b(self):
        corner_permutation = self.corner_permutation.copy()
        corner_orientation = self.corner_orientation.copy()
        edge_permutation = self.edge_permutation.copy()
        edge_orientation = self.edge_orientation.copy()

        corner_sources = [3, 2, 6, 7]
        corner_destinations = [2, 6, 7, 3]
        corner_changes = [1, 2, 1, 2]
        edge_sources = [3, 10, 7, 11]
        edge_destinations = [10, 7, 11, 3]
        for edge_destination, edge_source in zip(edge_destinations, edge_sources):
            edge_permutation[edge_destination] = self.edge_permutation[edge_source]
            edge_orientation[edge_destination] = (self.edge_orientation[edge_source] + 1) % 2

        
        for corner_destination, corner_source, corner_change in zip(corner_destinations, corner_sources, corner_changes):
            corner_permutation[corner_destination] = self.corner_permutation[corner_source]
            corner_orientation[corner_destination] = (self.corner_orientation[corner_source] + corner_change) % 3

        return CubeState(
            corner_permutation,
            corner_orientation,
            edge_permutation,
            edge_orientation
        )

    def move_r(self):
        corner_permutation = self.corner_permutation.copy()
        corner_orientation = self.corner_orientation.copy()
        edge_permutation = self.edge_permutation.copy()
        edge_orientation = self.edge_orientation.copy()

        corner_sources = [0, 3, 7, 4]
        corner_destinations = [3, 7, 4, 0]
        corner_changes = [1, 2, 1, 2]
        edge_sources = [0, 11, 4, 8]
        edge_destinations = [11, 4, 8, 0]
        for edge_destination, edge_source in zip(edge_destinations, edge_sources):
            edge_permutation[edge_destination] = self.edge_permutation[edge_source]
            edge_orientation[edge_destination] = self.edge_orientation[edge_source]

        
        for corner_destination, corner_source, corner_change in zip(corner_destinations, corner_sources, corner_changes):
            corner_permutation[corner_destination] = self.corner_permutation[corner_source]
            corner_orientation[corner_destination] = (self.corner_orientation[corner_source] + corner_change) % 3

        return CubeState(
            corner_permutation,
            corner_orientation,
            edge_permutation,
            edge_orientation
        )

    def move_l(self):
        corner_permutation = self.corner_permutation.copy()
        corner_orientation = self.corner_orientation.copy()
        edge_permutation = self.edge_permutation.copy()
        edge_orientation = self.edge_orientation.copy()

        corner_sources = [1, 5, 6, 2]
        corner_destinations = [5, 6, 2, 1]
        corner_changes = [2, 1, 2, 1]
        edge_sources = [2, 9, 6, 10]
        edge_destinations = [9, 6, 10, 2]
        for edge_destination, edge_source in zip(edge_destinations, edge_sources):
            edge_permutation[edge_destination] = self.edge_permutation[edge_source]
            edge_orientation[edge_destination] = self.edge_orientation[edge_source]

        
        for corner_destination, corner_source, corner_change in zip(corner_destinations, corner_sources, corner_changes):
            corner_permutation[corner_destination] = self.corner_permutation[corner_source]
            corner_orientation[corner_destination] = (self.corner_orientation[corner_source] + corner_change) % 3

        return CubeState(
            corner_permutation,
            corner_orientation,
            edge_permutation,
            edge_orientation
        )

    def apply_move(self, move):
        move_functions = {
            "F": "move_f",
            "B": "move_b",
            "R": "move_r",
            "L": "move_l",
            "U": "move_u",
            "D": "move_d"
        }

        face = move[0]
        suffix = move[1:]

        if suffix == "":
            rep = 1
        elif suffix == "2":
            rep = 2
        elif suffix == "'":
            rep = 3
        else:
            raise ValueError("Invalid move suffix")

        state = self
        method_name = move_functions[face]

        for reps in range(rep):
            method = getattr(state, method_name)
            state = method()
            
        return state

    def apply_sequence(self, moves):
        state = self

        for move in moves:
            state = state.apply_move(move)
        
        return state


    def key(self):
        return (
            tuple(self.corner_permutation),
            tuple(self.corner_orientation),
            tuple(self.edge_permutation),
            tuple(self.edge_orientation),
        )
              

corner_dictionary = {
    0: "URF",
    1: "UFL",
    2: "ULB",
    3: "UBR",
    4: "DFR",
    5: "DLF",
    6: "DBL",
    7: "DRB"
}
edge_dictionary = {
    0:"UR",
    1:"UF",
    2:"UL",
    3:"UB",
    4:"DR",
    5:"DF",
    6:"DL",
    7:"DB",
    8:"FR",
    9:"FL",
    10:"BL",
    11:"BR",
}

