from makefilegen import UniqueList

def test_unique_list():
    # Create a UniqueList
    ul = UniqueList([1, 2, 3, 2, 4, 1, 5])
    assert list(ul) == [1, 2, 3, 4, 5]  # Duplicates should be removed
    
    # Add elements
    ul.add(6)
    ul.add(3)  # Won't be added again
    assert list(ul) == [1, 2, 3, 4, 5, 6]
    
    # Use append (maintains uniqueness)
    ul.append(7)
    ul.append(1)  # Won't be added again
    assert list(ul) == [1, 2, 3, 4, 5, 6, 7]
    
    # Set operations
    ul2 = UniqueList([4, 5, 6, 7, 8])
    assert list(ul2) == [4, 5, 6, 7, 8]
    
    union_result = set(ul).union(ul2)
    assert union_result == {1, 2, 3, 4, 5, 6, 7, 8}
    
    intersection_result = set(ul).intersection(ul2)
    assert intersection_result == {4, 5, 6, 7}
    
    difference_result = set(ul).difference(ul2)
    assert difference_result == {1, 2, 3}
    
    symmetric_diff_result = set(ul).symmetric_difference(ul2)
    assert symmetric_diff_result == {1, 2, 3, 8}
    
    # First and last elements
    assert ul.first() == 1
    assert ul.last() == 7
    
    # Works with standard list operations
    assert len(ul) == 7
    assert 3 in ul
    assert 4 in ul
    assert ul.index(3) == 2  # 4 should be at index 2
    
    # Slicing works too
    first_three = ul[:3]
    assert list(first_three) == [1, 2, 3]
