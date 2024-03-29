import os
import os.path
import random
import sys
import time

from similaritem import utils

random.seed(1786)
HASH_BUCKETS = utils.L_MAX_32_BIT_INT  # largest 32bit unsigned-integer prime


def usage():
    info = """
    python similaritem.main [-k shingle-size] [-t threshold] [-sig signature-size] -path
    Where
        - path: is a path to a file or directory containing text documents
        - k   : is the size of the shingles. Defaults to 9
        - t   : is the threshold for documents signatures, so documents will be considered similar. Defaults to .8
        - sig : document signature size. Defaults to 100
    """

    print(info)


def main(path, shingle_size=9, threshold=.8, signature_size=100):
    files = (os.path.join(path, file) for file in os.listdir(path) if os.path.isfile(os.path.join(path, file)))
    documents_shingles = create_shingles_from_files(files, shingle_size)
    documents_shingles_hashes = hash_documents_shingles(documents_shingles, HASH_BUCKETS)

    start = time.time()
    jaccard_similarities = compare_sets_jaccard(documents_shingles_hashes)
    end = time.time()
    jaccard_time = end - start

    print('The following jaccard similarities between the k={k} '.format(k=shingle_size) +
          'k-shingles of all pairs of documents were found in ' +
          '{duration} seconds:\n'
          .format(k=shingle_size, duration=end - start) +
          '\n'.join('{doc_a} \t - {doc_b}: \t {jaccard_sim}'
                    .format(doc_a=pair[0][0], doc_b=pair[0][1], jaccard_sim=pair[1]) for pair in
                    jaccard_similarities))

    start = time.time()
    document_signatures = create_signatures_from_shingles(documents_shingles_hashes, signature_size)
    end = time.time()
    building_signatures = end - start

    start = time.time()
    signature_similarities = compare_sets_signature(document_signatures)
    end = time.time()
    signatures_time = end - start
    print('The following similarities of signatures between the '
          'n={n} sized signatures of all pairs of documents were'.format(n=signature_size) +
          'found in {duration} seconds:\n'.format(duration=signatures_time) +
          '\n'.join('{doc_a} \t - {doc_b}: \t {sig_sim}'
                    .format(doc_a=pair[0][0], doc_b=pair[0][1], sig_sim=pair[1]) for pair in
                    signature_similarities))

    n_bands, n_rows = utils.compute_index_measures(signature_size, threshold)
    start = time.time()
    similar_docs = find_similar_docs_using_lsh(document_signatures, n_rows, n_bands, threshold)
    end = time.time()
    lsh_time = end - start
    lsh_out = 'Using LSH with a threshold of {t} the following '.format(t=threshold) +\
              'document pairs were found to be similar in ' +\
              '{duration} seconds :\n'.format(duration=lsh_time)
    if len(similar_docs) > 0:
        lsh_out += '\n'.join('{doc_a} \t - {doc_b}: \t {sim}'
                             .format(doc_a=lsh_pair[0][0], doc_b=lsh_pair[0][1], sim=lsh_pair[1]) for lsh_pair in
                             similar_docs)
    else:
        lsh_out += 'None'
    print(lsh_out)

    print('Summary for times: \n'
          'Jaccard:\t{jaccard}\n'
          'Signatures:\t{sig}\n'
          'LSH:\t\t{lsh}\n'
          '-------------------------------------\n'
          'Building Signatures:\t{build_sig_time}'.format(jaccard=jaccard_time, build_sig_time=building_signatures, sig=signatures_time,
                                   lsh=lsh_time))


def hash_documents_shingles(documents, hash_buckets):
    document_hashes = dict()

    for k, shingles in documents.items():
        document_hashes[k] = utils.hash_shingles(shingles, hash_buckets)

    return document_hashes


def create_signatures_from_shingles(documents_hashes, signature_size):
    documents_signatures = {}
    min_hash_funcs = utils.generate_hash_functions(signature_size, HASH_BUCKETS)

    for doc_id, doc_shingle_hashes in documents_hashes.items():
        documents_signatures[doc_id] = utils.create_min_hash_signature(doc_shingle_hashes, min_hash_funcs)

    return documents_signatures


def create_shingles_from_files(files, shingle_size):
    documents = {}
    for file in files:
        documents[file] = utils.create_shingles_from_file(file, shingle_size)

    return documents


def compare_sets_jaccard(documents_hashes):
    keys = list(documents_hashes.keys())
    pairs = []
    n = len(keys)

    for i in range(n):
        for j in range(i + 1, n):
            pairs.append((keys[i], keys[j]))

    jaccard_similarities = []

    for pair in pairs:
        jaccard_similarities.append(
            (pair, utils.compute_jaccard_simularity(documents_hashes[pair[0]], documents_hashes[pair[1]])))

    return jaccard_similarities


def compare_sets_signature(document_signatures):
    keys = list(document_signatures.keys())
    pairs = []

    n = len(keys)
    for i in range(n):
        for j in range(i + 1, n):
            pairs.append((keys[i], keys[j]))

    return utils.check_signature_similarity(pairs, document_signatures, 0)


def find_similar_docs_using_lsh(document_signatures, n_rows, n_bands, threshold):
    candidate_pairs = utils.create_lsh_candidate_pairs(document_signatures, n_rows=n_rows, n_bands=n_bands,
                                                       hash_buckets=HASH_BUCKETS)
    similar_docs = utils.check_signature_similarity(candidate_pairs, document_signatures, threshold)

    return similar_docs


if __name__ == '__main__':

    argc = len(sys.argv)
    if argc < 3:
        usage()
        sys.exit(1)

    path = None
    shingle_size = 9
    threshold = 0.8
    signature_size = 100
    path = None

    for i in range(1, argc, 2):
        if sys.argv[i] == '-k':
            if argc < i + 1:
                usage()
                raise RuntimeError('Missing parameter: -k')

            try:
                shingle_size = int(sys.argv[i + 1])
            except ValueError:
                usage()
                raise RuntimeError('-k should be an integer')

        elif sys.argv[i] == '-t':
            if argc < i + 1:
                usage()
                raise RuntimeError('Missing parameter: -t')
            try:
                threshold = float(sys.argv[i + 1])
            except ValueError:
                usage()
                raise RuntimeError('-t should be a float value')

        elif sys.argv[i] == '-path':
            if argc < i + 1:
                usage()
                raise RuntimeError('Missing parameter: -path')

            path = sys.argv[i + 1]

            if not os.path.isdir(path):
                usage()
                raise RuntimeError('Path is expected to be a folder with multiple documents')
        elif sys.argv[i] == '-sig':
            if argc < i + 1:
                usage()
                raise RuntimeError('Missing parameter: -sig')

            try:
                signature_size = int(sys.argv[i + 1])
            except ValueError:
                usage()
                raise RuntimeError('-sig should be an integer')

        else:
            usage()
            raise RuntimeError('Unknown parameter {}'.format(sys.argv[i]))

    main(path, shingle_size, threshold, signature_size)
