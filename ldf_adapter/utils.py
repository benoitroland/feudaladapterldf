import copy

def dictdiff(old, new):
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
    res = copy.deepcopy(lhs)
    for k in rhs:
        if isinstance(rhs[k], dict) and k in res and isinstance(res[k], dict):
            res[k] = dictmerge(res[k], rhs[k])
        else:
            res[k] = rhs[k]

    return res
