*/*
MIT License

Copyright 2021 Moritz Gütlein

This code was originally published under the Apache 2.0 License (http://www.apache.org/licenses/LICENSE-2.0) in 2021.
In 2025, it has been relicensed under the MIT License (https://choosealicense.com/licenses/mit/) with the explicit permission of all copyright holders.
*/
#include "OrchestrationImpl.h"
using namespace daceDS;

std::vector<std::string> Orchestration::methods = {
    "ctrl"/*,
    "status"*/};

void OrchestrationImpl::ctrl(OrchestrationTopicMetadata& ometa, datamodel::CtrlMsg& ctrl) {
    if (ctrl.Command == "terminate") {
        cout << "I should terminate " << endl;
        cout << "I should terminate " << endl;
        cout << "I should terminate " << endl;
        cout << "I should terminate " << endl;
        wrapper->endWrapper();
    } else if (ctrl.Command == "die" || ctrl.Command == "kill") {
        cout << "should die abruptly " << endl;
        cout << "should die abruptly " << endl;
        cout << "should die abruptly " << endl;
        cout << "should die abruptly " << endl;
        wrapper->killWrapper();
        exit(1);
    } else {
        cout << "handleOrchestrationCtrl request=" << ctrl.Command << endl;
        cout << "handleOrchestrationCtrl request=" << ctrl.Command << endl;
        cout << "handleOrchestrationCtrl request=" << ctrl.Command << endl;
        cout << "handleOrchestrationCtrl request=" << ctrl.Command << endl;
    }
}

//void OrchestrationImpl::status(OrchestrationTopicMetadata& ometa, datamodel::StatusMsg& state) {
    //cout << "Command::STATUS action=" << state.Action << endl;
//}
