// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title AgentVerifier
 * @dev A simple blockchain logging system that records agent actions
 */
contract AgentVerifier {
    // Structure to store action data for each agent
    struct ActionData {
        bytes32 hash;      // Hash of the action data
        string cid;        // Content identifier (e.g., IPFS CID)
        uint256 ts;        // Timestamp of the action
    }

    // Mapping from agent address to their actions
    mapping(address => ActionData[]) public agentActions;

    // Event emitted when an action is recorded
    event ActionRecorded(
        address indexed agent,
        bytes32 hash,
        string cid,
        uint256 ts,
        uint256 indexed actionIndex
    );

    /**
     * @dev Records an action for the calling agent
     * @param _hash The hash of the action data
     * @param _cid The content identifier (e.g., IPFS CID)
     * @param _ts The timestamp of the action
     */
    function recordAction(
        bytes32 _hash,
        string memory _cid,
        uint256 _ts
    ) external {
        // Create new action data
        ActionData memory newAction = ActionData({
            hash: _hash,
            cid: _cid,
            ts: _ts
        });

        // Store the action for the caller
        agentActions[msg.sender].push(newAction);

        // Get the index of the newly added action
        uint256 actionIndex = agentActions[msg.sender].length - 1;

        // Emit event with action details
        emit ActionRecorded(msg.sender, _hash, _cid, _ts, actionIndex);
    }

    /**
     * @dev Retrieves the number of actions for a specific agent
     * @param _agent The address of the agent
     * @return The number of actions recorded for the agent
     */
    function getActionCount(address _agent) external view returns (uint256) {
        return agentActions[_agent].length;
    }

    /**
     * @dev Retrieves a specific action for an agent
     * @param _agent The address of the agent
     * @param _index The index of the action
     * @return hash The hash of the action
     * @return cid The content identifier
     * @return ts The timestamp
     */
    function getAction(address _agent, uint256 _index)
        external
        view
        returns (
            bytes32 hash,
            string memory cid,
            uint256 ts
        )
    {
        require(_index < agentActions[_agent].length, "Action index out of bounds");
        ActionData memory action = agentActions[_agent][_index];
        return (action.hash, action.cid, action.ts);
    }

    /**
     * @dev Retrieves all actions for a specific agent
     * @param _agent The address of the agent
     * @return An array of all actions for the agent
     */
    function getAllActions(address _agent) external view returns (ActionData[] memory) {
        return agentActions[_agent];
    }
}

