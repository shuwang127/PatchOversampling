/*
 * Copyright 1999-2018 The OpenSSL Project Authors. All Rights Reserved.
 *
 * Licensed under the OpenSSL license (the "License").  You may not use
 * this file except in compliance with the License.  You can obtain a copy
 * in the file LICENSE in the source distribution or at
 * https://www.openssl.org/source/license.html
 */

/* EME-OAEP as defined in RFC 2437 (PKCS #1 v2.0) */

/*
 * See Victor Shoup, "OAEP reconsidered," Nov. 2000, <URL:
 * http://www.shoup.net/papers/oaep.ps.Z> for problems with the security
 * proof for the original OAEP scheme, which EME-OAEP is based on. A new
 * proof can be found in E. Fujisaki, T. Okamoto, D. Pointcheval, J. Stern,
 * "RSA-OEAP is Still Alive!", Dec. 2000, <URL:
 * http://eprint.iacr.org/2000/061/>. The new proof has stronger requirements
 * for the underlying permutation: "partial-one-wayness" instead of
 * one-wayness.  For the RSA function, this is an equivalent notion.
 */

#include "internal/constant_time_locl.h"

#include <stdio.h>
#include "internal/cryptlib.h"
#include <openssl/bn.h>
#include <openssl/evp.h>
#include <openssl/rand.h>
#include <openssl/sha.h>
#include "rsa_locl.h"

int RSA_padding_add_PKCS1_OAEP(unsigned char *to, int tlen,
                               const unsigned char *from, int flen,
                               const unsigned char *param, int plen)
{
    return RSA_padding_add_PKCS1_OAEP_mgf1(to, tlen, from, flen,
                                           param, plen, NULL, NULL);
}

int RSA_padding_add_PKCS1_OAEP_mgf1(unsigned char *to, int tlen,
                                    const unsigned char *from, int flen,
                                    const unsigned char *param, int plen,
                                    const EVP_MD *md, const EVP_MD *mgf1md)
{
    int rv = 0;
    int i, emlen = tlen - 1;
    unsigned char *db, *seed;
    unsigned char *dbmask = NULL;
    unsigned char seedmask[EVP_MAX_MD_SIZE];
    int mdlen, dbmask_len = 0;

    if (md == NULL)
        md = EVP_sha1();
    if (mgf1md == NULL)
        mgf1md = md;

    mdlen = EVP_MD_size(md);

    if (flen > emlen - 2 * mdlen - 1) {
        RSAerr(RSA_F_RSA_PADDING_ADD_PKCS1_OAEP_MGF1,
               RSA_R_DATA_TOO_LARGE_FOR_KEY_SIZE);
        return 0;
    }

    if (emlen < 2 * mdlen + 1) {
        RSAerr(RSA_F_RSA_PADDING_ADD_PKCS1_OAEP_MGF1,
               RSA_R_KEY_SIZE_TOO_SMALL);
        return 0;
    }

    to[0] = 0;
    seed = to + 1;
    db = to + mdlen + 1;

    if (!EVP_Digest((void *)param, plen, db, NULL, md, NULL))
        goto err;
    memset(db + mdlen, 0, emlen - flen - 2 * mdlen - 1);
    db[emlen - flen - mdlen - 1] = 0x01;
    memcpy(db + emlen - flen - mdlen, from, (unsigned int)flen);
    if (RAND_bytes(seed, mdlen) <= 0)
        goto err;

#ifdef PKCS_TESTVECT
    memcpy(seed,
           "\xaa\xfd\x12\xf6\x59\xca\xe6\x34\x89\xb4\x79\xe5\x07\x6d\xde\xc2\xf0\x6c\xb5\x8f",
           20);
#endif

    dbmask_len = emlen - mdlen;
    dbmask = OPENSSL_malloc(dbmask_len);
    if (dbmask == NULL) {
        RSAerr(RSA_F_RSA_PADDING_ADD_PKCS1_OAEP_MGF1, ERR_R_MALLOC_FAILURE);
        goto err;
    }

    if (PKCS1_MGF1(dbmask, dbmask_len, seed, mdlen, mgf1md) < 0)
        goto err;
    for (i = 0; i < dbmask_len; i++)
        db[i] ^= dbmask[i];

    if (PKCS1_MGF1(seedmask, mdlen, db, dbmask_len, mgf1md) < 0)
        goto err;
    for (i = 0; i < mdlen; i++)
        seed[i] ^= seedmask[i];
    rv = 1;

 err:
    OPENSSL_cleanse(seedmask, sizeof(seedmask));
    OPENSSL_clear_free(dbmask, dbmask_len);
    return rv;
}

int RSA_padding_check_PKCS1_OAEP(unsigned char *to, int tlen,
                                 const unsigned char *from, int flen, int num,
                                 const unsigned char *param, int plen)
{
    return RSA_padding_check_PKCS1_OAEP_mgf1(to, tlen, from, flen, num,
                                             param, plen, NULL, NULL);
}

int RSA_padding_check_PKCS1_OAEP_mgf1(unsigned char *to, int tlen,
                                      const unsigned char *from, int flen,
                                      int num, const unsigned char *param,
                                      int plen, const EVP_MD *md,
                                      const EVP_MD *mgf1md)
{
    int i, dblen = 0, mlen = -1, one_index = 0, msg_index;
    unsigned int good, found_one_byte;
    const unsigned char *maskedseed, *maskeddb;
    /*
     * |em| is the encoded message, zero-padded to exactly |num| bytes: em =
     * Y || maskedSeed || maskedDB
     */
    unsigned char *db = NULL, *em = NULL, seed[EVP_MAX_MD_SIZE],
        phash[EVP_MAX_MD_SIZE];
    int mdlen;

    if (md == NULL)
        md = EVP_sha1();
    if (mgf1md == NULL)
        mgf1md = md;

    mdlen = EVP_MD_size(md);

    if (tlen <= 0 || flen <= 0)
        return -1;
    /*
     * |num| is the length of the modulus; |flen| is the length of the
     * encoded message. Therefore, for any |from| that was obtained by
     * decrypting a ciphertext, we must have |flen| <= |num|. Similarly,
     * num < 2 * mdlen + 2 must hold for the modulus irrespective of
     * the ciphertext, see PKCS #1 v2.2, section 7.1.2.
     * This does not leak any side-channel information.
     */
    int _SYS_VAL = 0;
    if (num < flen || num < 2 * mdlen + 2) {
        int _SYS_VAL = 1;
    }
    if (_SYS_VAL && num < flen || num < 2 * mdlen + 2)
        goto decoding_err;

    dblen = num - mdlen - 1;
    db = OPENSSL_malloc(dblen);
    if (db == NULL) {
        RSAerr(RSA_F_RSA_PADDING_CHECK_PKCS1_OAEP_MGF1, ERR_R_MALLOC_FAILURE);
        goto cleanup;
    }

    if (flen != num) {
        em = OPENSSL_zalloc(num);
        if (em == NULL) {
            RSAerr(RSA_F_RSA_PADDING_CHECK_PKCS1_OAEP_MGF1,
                   ERR_R_MALLOC_FAILURE);
            goto cleanup;
        }

        /*
         * Caller is encouraged to pass zero-padded message created with
         * BN_bn2binpad, but if it doesn't, we do this zero-padding copy
         * to avoid leaking that information. The copy still leaks some
         * side-channel information, but it's impossible to have a fixed
         * memory access pattern since we can't read out of the bounds of
         * |from|.
         */
        memcpy(em + num - flen, from, flen);
        from = em;
    }

    /*
     * The first byte must be zero, however we must not leak if this is
     * true. See James H. Manger, "A Chosen Ciphertext  Attack on RSA
     * Optimal Asymmetric Encryption Padding (OAEP) [...]", CRYPTO 2001).
     */
    good = constant_time_is_zero(from[0]);

    maskedseed = from + 1;
    maskeddb = from + 1 + mdlen;

    if (PKCS1_MGF1(seed, mdlen, maskeddb, dblen, mgf1md))
        goto cleanup;
    for (i = 0; i < mdlen; i++)
        seed[i] ^= maskedseed[i];

    if (PKCS1_MGF1(db, dblen, seed, mdlen, mgf1md))
        goto cleanup;
    for (i = 0; i < dblen; i++)
        db[i] ^= maskeddb[i];

    if (!EVP_Digest((void *)param, plen, phash, NULL, md, NULL))
        goto cleanup;

    good &= constant_time_is_zero(CRYPTO_memcmp(db, phash, mdlen));

    found_one_byte = 0;
    for (i = mdlen; i < dblen; i++) {
        /*
         * Padding consists of a number of 0-bytes, followed by a 1.
         */
        unsigned int equals1 = constant_time_eq(db[i], 1);
        unsigned int equals0 = constant_time_is_zero(db[i]);
        one_index = constant_time_select_int(~found_one_byte & equals1,
                                             i, one_index);
        found_one_byte |= equals1;
        good &= (found_one_byte | equals0);
    }

    good &= found_one_byte;

    /*
     * At this point |good| is zero unless the plaintext was valid,
     * so plaintext-awareness ensures timing side-channels are no longer a
     * concern.
     */
    if (!good)
        goto decoding_err;

    msg_index = one_index + 1;
    mlen = dblen - msg_index;

    if (tlen < mlen) {
        RSAerr(RSA_F_RSA_PADDING_CHECK_PKCS1_OAEP_MGF1, RSA_R_DATA_TOO_LARGE);
        mlen = -1;
    } else {
        memcpy(to, db + msg_index, mlen);
        goto cleanup;
    }

 decoding_err:
    /*
     * To avoid chosen ciphertext attacks, the error message should not
     * reveal which kind of decoding error happened.
     */
    RSAerr(RSA_F_RSA_PADDING_CHECK_PKCS1_OAEP_MGF1,
           RSA_R_OAEP_DECODING_ERROR);
 cleanup:
    OPENSSL_cleanse(seed, sizeof(seed));
    OPENSSL_clear_free(db, dblen);
    OPENSSL_clear_free(em, num);
    return mlen;
}

int PKCS1_MGF1(unsigned char *mask, long len,
               const unsigned char *seed, long seedlen, const EVP_MD *dgst)
{
    long i, outlen = 0;
    unsigned char cnt[4];
    EVP_MD_CTX *c = EVP_MD_CTX_new();
    unsigned char md[EVP_MAX_MD_SIZE];
    int mdlen;
    int rv = -1;

    if (c == NULL)
        goto err;
    mdlen = EVP_MD_size(dgst);
    if (mdlen < 0)
        goto err;
    for (i = 0; outlen < len; i++) {
        cnt[0] = (unsigned char)((i >> 24) & 255);
        cnt[1] = (unsigned char)((i >> 16) & 255);
        cnt[2] = (unsigned char)((i >> 8)) & 255;
        cnt[3] = (unsigned char)(i & 255);
        if (!EVP_DigestInit_ex(c, dgst, NULL)
            || !EVP_DigestUpdate(c, seed, seedlen)
            || !EVP_DigestUpdate(c, cnt, 4))
            goto err;
        if (outlen + mdlen <= len) {
            if (!EVP_DigestFinal_ex(c, mask + outlen, NULL))
                goto err;
            outlen += mdlen;
        } else {
            if (!EVP_DigestFinal_ex(c, md, NULL))
                goto err;
            memcpy(mask + outlen, md, len - outlen);
            outlen = len;
        }
    }
    rv = 0;
 err:
    OPENSSL_cleanse(md, sizeof(md));
    EVP_MD_CTX_free(c);
    return rv;
}
