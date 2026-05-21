import asyncio 
from caproto.server import PVGroup, pvproperty, SubGroup, ioc_arg_parser, run
from caproto.threading.client import Context 
from textwrap import dedent

class MyIOC(PVGroup): 
    """
    A local PV that will hold the mirrored value from the other IOC 
    """
    mirrored_pv = pvproperty(value=1.0, doc="Mirrored value from remote IOC") 
    
    def __init__(self, *args, **kwargs): 
        super().__init__(*args, **kwargs) 
        # 1. Start the client context 
        self.ctx = Context() 
        # 2. Start an asyncio background task to monitor the remote PV
        self.loop = asyncio.get_event_loop()
        self.loop.create_task(self.monitor_remote_pv())
        self.loop.run_forever()

    async def monitor_remote_pv(self): 
        # 3. Connect to the remote PV 
        pv_name = "MR1L0:HOMS:MMS:PITCH.RBV" 
        pv, = await self.ctx.get_pvs(pv_name) 

        # 4. Subscribe to updates 
        async for response in pv.subscribe(data_type='time'): 
            # Update local PV whenever remote value changes 
            await self.mirrored_pv.write(response.data[0]) 

if __name__ == "__main__": 
    ioc_options, run_options = ioc_arg_parser(default_prefix='simple:',
            desc = dedent(MyIOC.__doc__))
    #ioc_options, run_options = ioc_run(MyIOC.pvspec)
    ioc = MyIOC(**ioc_options)
    #ioc_run(MyIOC.pvspec, **run_options)
    run(ioc.pvdb, **run_options)
