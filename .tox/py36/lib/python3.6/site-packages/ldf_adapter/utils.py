import copy

def dictdiff(old, new):
    """Return the difference between two dicts.

    Returns a dictionary mapping the keys from `old` and `new` to tuples `(old_value, new_value)`.
    A value of `None` in one of the elements of the tuple indicates that the key was not present in
    the respective dictionary.

    Does not distinguishing between missing keys and values of `None`.

    Arguments:
    old -- The first dictionary (type: dict)
    new -- The other dictionary (type: dict)
    """
    def _dictdiff(old, new):
        for k in new:
            if isinstance(new.get(k), dict) and isinstance(old.get(k), dict):
                subdiff = dict(_dictdiff(old[k], new[k]))
                if subdiff:
                    yield (k, subdiff)
            elif old.get(k) != new.get(k):
                yield (k, (old.get(k), new.get(k)))

    return dict(_dictdiff(old, new))

def log_dictdiff(diff, log_function=print, prefix=''):
    """Print the given dict-difference.

    Arguments:
    diff -- The dict diff as returned by `dictdiff` (type: dict)
    log_function -- The function to be used for printing (type: lambda str: None)
    """
    for k,v in diff.items():
        if isinstance(v, dict):
            log_dictdiff(v, log_function, "{}/".format(k))
        else:
            (old, new) = v
            if old:
                log_function("Updating {}{} from '{}' to '{}'".format(prefix, k, old, new))
            else:
                log_function("Setting {}{} to '{}'".format(prefix, k, new))

def dictmerge(lhs, rhs):
    """Merge two dicts recusively."""
    res = copy.deepcopy(lhs)
    for k in rhs:
        if isinstance(rhs[k], dict) and k in res and isinstance(res[k], dict):
            res[k] = dictmerge(res[k], rhs[k])
        else:
            res[k] = rhs[k]

    return res
