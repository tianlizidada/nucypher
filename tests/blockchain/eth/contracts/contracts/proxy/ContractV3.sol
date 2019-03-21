pragma solidity ^0.5.3;


import "./ContractV2.sol";


contract ContractV3 is ContractV2 {

    uint256 public anotherStorageValue;

    constructor(uint256 _storageValueToCheck)
        public
        ContractV2(_storageValueToCheck)
    {
    }

    function setAnotherStorageValue(uint256 _value) public {
        anotherStorageValue = _value * 2;
    }

    function verifyState(address _testTarget) public onlyWhileUpgrading {
        super.verifyState(_testTarget);
        require(delegateGet(_testTarget, "anotherStorageValue()") == anotherStorageValue);
    }
}
