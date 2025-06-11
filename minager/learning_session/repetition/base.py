class BaseLearningStrategy:
    """
    Base learning strategy. Defines common to all learning strategies interface.
    """

    def study_node(self, node_learning_stats, repetition_rating):
        """
        Handle user mind palace node repetition.

        Args:
            node_learning_stats: Mind palace node learning statistics.
            repetition_rating: New repetition rating.
        """
        raise NotImplementedError
