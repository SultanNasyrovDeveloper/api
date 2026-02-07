from minager.core.lexorank import Lexorank


def visualize_between(prev, next_):
    """Visualize what happens in get_lexorank_in_between."""
    print(f"\n{'=' * 60}")
    print(f"Calculating rank between '{prev}' and '{next_}'")
    print(f"{'=' * 60}")

    # Align ranks
    prev_aligned, next_aligned = Lexorank.align_ranks(prev, next_)
    print(f"Aligned: '{prev_aligned}' and '{next_aligned}'")

    # Parse to numbers
    prev_parts = Lexorank.parse_rank(prev_aligned)
    next_parts = Lexorank.parse_rank(next_aligned)
    print(f"As numbers: {prev_parts} and {next_parts}")

    # Calculate difference
    total_diff = 0
    n = len(prev_parts)

    print('\nCalculating total difference:')
    for i in range(n):
        idx = n - i - 1
        prev_val = prev_parts[idx]
        next_val = next_parts[idx]

        print(f"  Position {idx}: {prev_val} vs {next_val}", end='')

        # Borrow logic
        if next_val < prev_val:
            next_val += Lexorank.base
            next_parts[idx] = next_val
            if idx > 0:
                next_parts[idx - 1] -= 1
            print(f" -> borrowed, next now {next_val}")
        else:
            print()

        diff = next_val - prev_val
        weight = Lexorank.base**i
        contribution = diff * weight
        total_diff += contribution
        print(f"    Difference: {diff} * {weight} = {contribution}")

    print(f"\nTotal difference: {total_diff}")
    print(f"Half difference: {total_diff // 2}")

    # Calculate middle
    middle_parts = []
    carry = 0

    print('\nCalculating middle:')
    for i in range(n):
        idx = n - i - 1
        prev_val = prev_parts[idx]
        weight = Lexorank.base**i

        to_add = (total_diff // 2) // weight % Lexorank.base
        middle_val = prev_val + to_add + carry
        carry = 0

        if middle_val >= Lexorank.base:
            carry = 1
            middle_val -= Lexorank.base

        middle_parts.insert(0, middle_val)

        print(f"  Position {idx}: {prev_val} + {to_add} + {carry} = {middle_val}")

    if carry:
        middle_parts.insert(0, 0)
        print(f"  Final carry: added 0 at beginning")

    result = Lexorank.format_rank(middle_parts)
    print(f"\nResult: {result} (as numbers: {middle_parts})")

    # Verify
    if prev and next_:
        assert prev < result < next_, f"FAIL: {prev} < {result} < {next_}"
    print('✓ Result is correctly between inputs')

    return result


def test_problematic_cases():
    """Test cases that might reveal bugs."""
    cases = [
        ('a', 'b'),
        ('aa', 'ab'),
        ('am', 'an'),
        ('az', 'ba'),  # Cross-boundary
        ('a', 'z'),
        ('', 'z'),
        ('a', ''),
        ('', ''),
        ('zz', 'zza'),  # Need to add digit
    ]

    for prev, next_ in cases:
        try:
            result = visualize_between(prev, next_)
            print(f"✓ Success: between '{prev}' and '{next_}' -> '{result}'")
        except Exception as e:
            print(f"✗ Error: {e}")
        print()


def test_increment_rank_overflow():
    """Test the overflow bug with large ranks."""
    print('\n=== Testing increment_rank overflow ===')

    # Test with a rank near the end
    test_rank = 'xxxyyzn'
    print(f"Test rank: {test_rank}")
    print(f"As numbers: {Lexorank.parse_rank(test_rank)}")

    try:
        result = Lexorank.increment_rank(test_rank, 10)
        print(f"Incremented: {result}")
        print(f"Comparison: '{test_rank}' < '{result}' = {test_rank < result}")

        if test_rank >= result:
            print(f"BUG CONFIRMED: {test_rank} >= {result}")
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()


def debug_step_calculation():
    """Debug the step calculation."""
    print('\n=== Debugging step calculation ===')

    for obj_count in [1, 2, 5, 10, 20, 50, 100]:
        rank_length = Lexorank.get_rank_length(obj_count)
        total_space = 26**rank_length
        step = int(total_space / obj_count - 0.5)

        print(
            f"Objects: {obj_count:3d}, Length: {rank_length}, "
            f"Total space: {total_space:15d}, Step: {step:15d}"
        )

        # Show what adding step to 'z'*8 would do
        max_rank_value = sum(25 * (26**i) for i in range(rank_length))
        print(f"  Max rank value: {max_rank_value:15d}")
        print(f"  Step > Max? {step > max_rank_value}")
