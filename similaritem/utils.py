import sys
import re
import random


def create_shingles_from_file(filepath, shingle_size):
    shingles = set()
    left_over = ''
    with open(filepath, 'r') as fp:
        for line in fp:
            working_line = left_over + line
            working_line = re.sub('\n', ' ', working_line)
            working_line = re.sub('\t', ' ', working_line)
            working_line = re.sub('[ ]{2,}', ' ', working_line)
            for i in range(len(working_line) - (shingle_size - 1)):
                shingles.add(working_line[i:i + shingle_size])
                left_over = working_line[-(shingle_size - 1):]

    return shingles


def hash_shingles(shingles, maxi):
    return {(hash(shingle) & maxi) for shingle in shingles}


def create_min_hash_signature(hashed_shingles, hash_funcs):
    signature = [sys.maxsize for _ in range(len(hash_funcs))]
    for shingle_hash in hashed_shingles:
        signature = tuple([min(hfunc(shingle_hash), val) for hfunc, val in zip(hash_funcs, signature)])

    return signature


def generate_hash_functions(n, hash_buckets):
    hash_funcs = []
    for _ in range(n):
        a = random.randint(1, 100)
        b = random.randint(1, 100)
        hash_funcs.append(lambda x: (a * x + b) % hash_buckets)

    return hash_funcs


def compute_index_measures(signature_size, threshold, high_recall=True):
    b, r = 2, 1
    n_bands, n_rows = None, None

    while b <= signature_size:

        if r >= signature_size:
            b, r = b + 1, 1

        if b * r == signature_size:
            t = (1.0 / b) ** (1.0 / r)

            if high_recall and t < threshold:
                n_bands, n_rows = b, r  # first pair corresponds to highest r (we don't want it too small)
                break
            elif not high_recall and t > threshold:
                n_bands, n_rows = b, r  # don't break... search for highest b (we don't want it too small)

        r += 1

    return n_bands, n_rows


def create_lsh_candidate_pairs(document_signatures, n_rows, n_bands, hash_buckets):
    buckets_in_bands = dict((band, {}) for band in range(n_bands))
    for doc_id, signature in document_signatures.items():
        for band in range(n_bands):
            bucket = hash(signature[band * n_rows:(band + 1) * n_rows]) & hash_buckets
            buckets_in_bands[band].setdefault(str(bucket), []).append(doc_id)

    candidates = (candidates for band, bucket in buckets_in_bands.items()
                  for k, candidates in bucket.items() if len(candidates) > 1)

    candidate_pairs = set()

    for candidate in candidates:
        for i in range(len(candidate)):
            for j in range(i + 1, len(candidate)):
                candidate_pairs.add((candidate[i], candidate[j]))

    return candidate_pairs


def check_signature_simularity(candidate_pairs, document_signatures, threshold):
    similar_docs = []
    for candidate_pair in candidate_pairs:
        sig_a = document_signatures[candidate_pair[0]]
        sig_b = document_signatures[candidate_pair[1]]
        sig_len = len(sig_a)
        equal_positions = 0
        for i in range(sig_len):
            if sig_a[i] == sig_b[i]:
                equal_positions += 1
        if (equal_positions / sig_len) >= threshold:
            similar_docs.append(candidate_pair)

    return similar_docs
