// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title FaceVerification
 * @notice Stores face-match verification records on-chain as tamper-evident proof.
 * @dev    Each record maps a SHA-256 data hash to metadata about the match.
 *         - registerMatch(): write a new record (costs gas)
 *         - verifyMatch():   check if a hash exists (free read)
 *         - getRecord():     retrieve full record details (free read)
 */
contract FaceVerification {

    // ───────── Types ─────────

    struct MatchRecord {
        address registrant;     // wallet that registered the match
        uint256 timestamp;      // block.timestamp when registered
        string  imageURL;       // public URL of the face image searched
        string  matchSource;    // URL / domain of the matched social-media post
        string  matchTitle;     // title / snippet of the matched post
        bool    exists;         // flag to distinguish from empty mapping slots
    }

    // ───────── State ─────────

    /// @notice dataHash → on-chain record
    mapping(bytes32 => MatchRecord) private records;

    /// @notice running count of records stored
    uint256 public recordCount;

    // ───────── Events ─────────

    event MatchRegistered(
        bytes32 indexed dataHash,
        address indexed registrant,
        string  imageURL,
        string  matchSource,
        uint256 timestamp
    );

    // ───────── Write ─────────

    /**
     * @notice Register a new face-match verification record.
     * @param _dataHash    SHA-256 hash of the combined match data
     * @param _imageURL    Public URL of the face image that was searched
     * @param _matchSource URL of the matching social-media post
     * @param _matchTitle  Title or snippet from the matching post
     */
    function registerMatch(
        bytes32 _dataHash,
        string calldata _imageURL,
        string calldata _matchSource,
        string calldata _matchTitle
    ) external {
        require(!records[_dataHash].exists, "Record already exists for this hash");

        records[_dataHash] = MatchRecord({
            registrant:  msg.sender,
            timestamp:   block.timestamp,
            imageURL:    _imageURL,
            matchSource: _matchSource,
            matchTitle:  _matchTitle,
            exists:      true
        });

        recordCount++;

        emit MatchRegistered(
            _dataHash,
            msg.sender,
            _imageURL,
            _matchSource,
            block.timestamp
        );
    }

    // ───────── Read ─────────

    /**
     * @notice Check whether a record exists for the given hash.
     * @param _dataHash The hash to look up
     * @return True if a record has been registered for this hash
     */
    function verifyMatch(bytes32 _dataHash) external view returns (bool) {
        return records[_dataHash].exists;
    }

    /**
     * @notice Retrieve the full record for a given hash.
     * @param _dataHash The hash to look up
     * @return registrant  Address that created the record
     * @return timestamp   Unix timestamp of registration
     * @return imageURL    Face image URL that was searched
     * @return matchSource URL of the matched post
     * @return matchTitle  Title/snippet of the matched post
     */
    function getRecord(bytes32 _dataHash)
        external
        view
        returns (
            address registrant,
            uint256 timestamp,
            string memory imageURL,
            string memory matchSource,
            string memory matchTitle
        )
    {
        require(records[_dataHash].exists, "No record found for this hash");
        MatchRecord storage r = records[_dataHash];
        return (r.registrant, r.timestamp, r.imageURL, r.matchSource, r.matchTitle);
    }
}
