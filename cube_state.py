class CubeState:
    #Constructor for cube state class
    def __init__(self, corner_permutation, corner_orientation, edge_permutation, edge_orientation):
        self.corner_permutation = corner_permutation.copy()
        self.corner_orientation = corner_orientation.copy()
        self.edge_permutation = edge_permutation.copy()
        self.edge_orientation = edge_orientation.copy()

    #Value of solved cube
    def __repr__(self):
        return (f"CubeState(corner_permutation={self.corner_permutation}, "
                f"corner_orientation={self.corner_orientation}, "
                f"edge_permutation={self.edge_permutation}, "
                f"edge_orientation={self.edge_orientation})")
    """
        Solved Cube:
                corner_permutation=[0, 1, 2, 3, 4, 5, 6, 7],
                corner_orientation=[0, 0, 0, 0, 0, 0, 0, 0],
                edge_permutation=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
                edge_orientation=[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    """

    @classmethod
    def solved(cls):
        return cls(
            corner_permutation=[0, 1, 2, 3, 4, 5, 6, 7],
            corner_orientation=[0, 0, 0, 0, 0, 0, 0, 0],
            edge_permutation=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
            edge_orientation=[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        )

    #Allows me to use equal sign to compare to a solved state
    def __eq__(self, other):
        return (self.corner_permutation == other.corner_permutation and
                self.corner_orientation == other.corner_orientation and
                self.edge_permutation == other.edge_permutation and
                self.edge_orientation == other.edge_orientation)

    #Function for checking if cube is solved or not
    def is_solved(self):
        if self == CubeState.solved():
            return True
        return False

    #Instance method for checking if cube is in a possible configuration or not
    def is_valid(self):
        if len(self.corner_orientation) != 8 or len(self.edge_orientation) != 12:
            return False
        if sorted(self.corner_permutation) != list(range(8)):
            return False
        if sorted(self.edge_permutation) != list(range(12)):
            return False
        if not all(num in [0, 1, 2] for num in self.corner_orientation): #Return False if any corner orientation is not 0, 1, or 2.
            return False
        if not all(num in [0, 1] for num in self.edge_orientation): #Return False if any edge orientation is not 0 or 1.
            return False
        return True

    #Moves Needed:
    # U, U2, D, D2, F, F2, B, B2, L, L2, R, R2
    # U', D', F', B', L', R'

    #Instance method for the first move (U Move)
    def move_u(self):
        corner_permutation = self.corner_permutation.copy()
        corner_orientation = self.corner_orientation.copy()
        edge_permutation = self.edge_permutation.copy()
        edge_orientation = self.edge_orientation.copy()

        corner_permutation.insert(0, corner_permutation.pop(3))
        edge_permutation.insert(0, edge_permutation.pop(3))

        return CubeState(
            corner_permutation,
            corner_orientation,
            edge_permutation,
            edge_orientation
        )

    #Instance method for the second move (D Move)
    def move_d(self):
        corner_permutation = self.corner_permutation.copy()
        corner_orientation = self.corner_orientation.copy()
        edge_permutation = self.edge_permutation.copy()
        edge_orientation = self.edge_orientation.copy()

        corner_permutation.insert(7, corner_permutation.pop(4))
        edge_permutation.insert(7, edge_permutation.pop(4))

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

        corner_sources = [0, 1, 5, 4] # source
        corner_destinations = [4, 0, 1, 5] # destination
        corner_changes = [2, 1, 2, 1] # changes

        edge_sources = [1, 9, 5, 8] # source
        edge_destinations = [8, 1, 9, 5] # destination

        for edge_destination, edge_source in zip(edge_destinations, edge_sources):
            edge_permutation[edge_destination] = self.edge_permutation[edge_source]
            edge_orientation[edge_destination] = (self.edge_orientation[edge_source] + 1) % 2

        
        for corner_destination, corner_source, corner_change in zip(corner_destinations, corner_sources, corner_changes):
            corner_permutation[corner_destination] = self.corner_permutation[corner_source]
            corner_orientation[corner_destination] = (self.corner_orientation[corner_source] + corner_change) % 3

        """
            Zip Implementation:
            
            destinations = [2, 4, 6]
            sources = [4, 6, 2]

            for destination, source in zip(destinations, sources):
                new_array[destination] = old_array[source]
        """

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

        corner_sources = [3, 2, 6, 7] # source
        corner_destinations = [2, 6, 7, 3] # destination
        corner_changes = [1, 2, 1, 2] # changes

        edge_sources = [3, 10, 7, 11] # source
        edge_destinations = [10, 7, 11, 3] # destination

        for edge_destination, edge_source in zip(edge_destinations, edge_sources):
            edge_permutation[edge_destination] = self.edge_permutation[edge_source]
            edge_orientation[edge_destination] = (self.edge_orientation[edge_source] + 1) % 2

        
        for corner_destination, corner_source, corner_change in zip(corner_destinations, corner_sources, corner_changes):
            corner_permutation[corner_destination] = self.corner_permutation[corner_source]
            corner_orientation[corner_destination] = (self.corner_orientation[corner_source] + corner_change) % 3

        """
            Zip Implementation:
            
            destinations = [2, 4, 6]
            sources = [4, 6, 2]

            for destination, source in zip(destinations, sources):
                new_array[destination] = old_array[source]
        """

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

        corner_sources = [0, 3, 7, 4] # source
        corner_destinations = [3, 7, 4, 0] # destination
        corner_changes = [1, 2, 1, 2] # changes

        edge_sources = [0, 11, 4, 8] # source
        edge_destinations = [11, 4, 8, 0] # destination

        for edge_destination, edge_source in zip(edge_destinations, edge_sources):
            edge_permutation[edge_destination] = self.edge_permutation[edge_source]
            edge_orientation[edge_destination] = self.edge_orientation[edge_source]

        
        for corner_destination, corner_source, corner_change in zip(corner_destinations, corner_sources, corner_changes):
            corner_permutation[corner_destination] = self.corner_permutation[corner_source]
            corner_orientation[corner_destination] = (self.corner_orientation[corner_source] + corner_change) % 3

        """
            Zip Implementation:
            
            destinations = [2, 4, 6]
            sources = [4, 6, 2]

            for destination, source in zip(destinations, sources):
                new_array[destination] = old_array[source]
        """

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

        corner_sources = [1, 5, 6, 2] # source
        corner_destinations = [5, 6, 2, 1] # destination
        corner_changes = [2, 1, 2, 1] # changes

        edge_sources = [2, 9, 6, 10] # source
        edge_destinations = [9, 6, 10, 2] # destination

        for edge_destination, edge_source in zip(edge_destinations, edge_sources):
            edge_permutation[edge_destination] = self.edge_permutation[edge_source]
            edge_orientation[edge_destination] = self.edge_orientation[edge_source]

        
        for corner_destination, corner_source, corner_change in zip(corner_destinations, corner_sources, corner_changes):
            corner_permutation[corner_destination] = self.corner_permutation[corner_source]
            corner_orientation[corner_destination] = (self.corner_orientation[corner_source] + corner_change) % 3

        """
            Zip Implementation:
            
            destinations = [2, 4, 6]
            sources = [4, 6, 2]

            for destination, source in zip(destinations, sources):
                new_array[destination] = old_array[source]
        """

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


        face = move[0] # grabs first letter to see which move
        suffix = move[1:] #checks for the suffix to see if its a 2x move or an inverse denoted by '

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

    def apply_sequence(self, moves): # apply scrambles using a list of strings
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


if __name__ == "__main__":
    cube = CubeState.solved()
    same_cube = CubeState.solved()
    moved_cube = cube.apply_move("F")

    print(cube.key() == same_cube.key())
    print(cube.key() == moved_cube.key())

    visited = {cube.key()}
    print(same_cube.key() in visited)
    print(moved_cube.key() in visited)
